"""
Paso 2: aplicar las reglas de detección de brechas candidatas a cada caso.

Entrada : datos/muestra.csv y casos/<version_id>/
Salida  : resultados/agentes.csv            (una fila por agente: rasgos extraídos)
          resultados/brechas_candidatas.csv (una fila por brecha candidata, para revisión manual)

Ejecutar desde la raíz del proyecto:
    python codigo/02_detectar_brechas.py

IMPORTANTE: este script SOBRESCRIBE brechas_candidatas.csv.
La revisión manual se hace en una copia: resultados/brechas_revisadas.csv
"""

import json
import re
from pathlib import Path

import pandas as pd
import yaml

RAIZ = Path(__file__).resolve().parent.parent
DIR_CASOS = RAIZ / "casos"
DIR_RESULTADOS = RAIZ / "resultados"

# Reglas automáticas: código -> (tipo del libro de códigos, descripción)
REGLAS = {
    "E1_roles":           ("E1", "Menciona un rol o nivel de confianza pero no configura 'roles'; el compilado aplica roles por defecto"),
    "E2_aprobar":         ("E2", "El compilado permite emitir una revisión APPROVE que el Markdown no menciona"),
    "E2_memoria":         ("E2", "El compilado activa memoria persistente (cache-memory) no declarada en el Markdown"),
    "E2_edicion":         ("E2", "El compilado se activa al editar comentarios ('edited') sin que el Markdown lo declare"),
    "E2_escritura":       ("E2", "El compilado tiene permisos de escritura que el Markdown no declara"),
    "E3_delegacion":      ("E3", "El body no tiene instrucciones propias (solo títulos) y la intención se delega a imports"),
    "E4_idtoken":         ("E4", "El Markdown pide id-token: write sin justificarlo en el body"),
    "E5_variantes":       ("E5", "Otros agentes del mismo repositorio usan exactamente los mismos imports"),
}

# Resultado esperado en los casos analizados a mano (validación de las reglas)
ESPERADO = {
    "gh-aw-pr-rereview.md": {"E1_roles", "E2_aprobar", "E2_memoria", "E2_edicion",
                             "E2_escritura", "E3_delegacion", "E4_idtoken", "E5_variantes"},
    "gh-aw-pr-review.md":   {"E1_roles", "E2_aprobar", "E2_memoria", "E2_escritura",
                             "E3_delegacion", "E4_idtoken", "E5_variantes"},
}


# ---------------------------------------------------------------------------
# Funciones de apoyo
# ---------------------------------------------------------------------------
def leer(ruta):
    return ruta.read_text(encoding="utf-8") if ruta.exists() else ""


def leer_yaml(texto):
    """Devuelve el YAML como diccionario, o None si no se puede leer."""
    try:
        datos = yaml.safe_load(texto or "")
        return datos if isinstance(datos, dict) else {}
    except yaml.YAMLError:
        return None


def obtener_on(d):
    """Python lee la clave 'on' de YAML como True; se buscan ambas."""
    if not isinstance(d, dict):
        return {}
    valor = d.get("on", d.get(True, {}))
    return valor if isinstance(valor, dict) else {}


def body_solo_titulos(body):
    lineas = [l.strip() for l in (body or "").splitlines() if l.strip()]
    return all(l.startswith("#") for l in lineas)


def permisos_write(perms):
    if isinstance(perms, dict):
        return {k for k, v in perms.items() if v == "write"}
    if perms == "write-all":
        return {"write-all"}
    return set()


def permisos_write_compilado(lock_yaml, lock_txt):
    """Permisos con 'write' en cualquier job del compilado.
    Usa la estructura YAML si se puede leer; si no, busca en el texto."""
    if lock_yaml and isinstance(lock_yaml.get("jobs"), dict):
        encontrados = set()
        for job in lock_yaml["jobs"].values():
            if isinstance(job, dict):
                encontrados |= permisos_write(job.get("permissions"))
        return encontrados
    return set(re.findall(r"^\s*([a-z][a-z-]*):\s*write\s*$", lock_txt, re.M))


def activa_por_edicion(lock_yaml, lock_txt):
    if lock_yaml:
        on = obtener_on(lock_yaml)
        return any(isinstance(c, dict) and "edited" in (c.get("types") or []) for c in on.values())
    # Sin estructura: buscar 'edited' antes de la sección 'jobs:'
    cabecera = re.split(r"^jobs:\s*$", lock_txt, maxsplit=1, flags=re.M)[0]
    return re.search(r"^\s*-\s*edited\s*$", cabecera, re.M) is not None


def metadatos(lock_txt):
    m = re.search(r"#\s*gh-aw-metadata:\s*(\{.*\})", lock_txt)
    if not m:
        return {}
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return {}


# ---------------------------------------------------------------------------
# Análisis de un caso
# ---------------------------------------------------------------------------
def analizar(caso):
    carpeta = DIR_CASOS / str(caso["version_id"])
    frontmatter = leer(carpeta / "frontmatter.yml")
    body = leer(carpeta / "body.md")
    lock_txt = leer(carpeta / "compilado.lock.yml")

    fm = leer_yaml(frontmatter)
    lock_yaml = leer_yaml(lock_txt)
    texto_md = frontmatter + "\n" + body
    fm = fm or {}

    meta = metadatos(lock_txt)
    roles = re.search(r'GH_AW_REQUIRED_ROLES:\s*"([^"]+)"', lock_txt)
    write_md = permisos_write(fm.get("permissions"))
    write_lock = permisos_write_compilado(lock_yaml, lock_txt)
    write_extra = sorted(write_lock - write_md - {"id-token"})
    perms = fm.get("permissions")

    # Rasgos del agente (tabla descriptiva)
    rasgos = {
        "version_id": caso["version_id"],
        "repo": caso["repository_id"],
        "agente": caso["path_md"],
        "es_validacion": caso.get("es_validacion", False),
        "frontmatter_legible": leer_yaml(frontmatter) is not None,
        "lock_legible_como_yaml": lock_yaml is not None,
        "n_imports": len(fm.get("imports") or []) if isinstance(fm.get("imports"), list) else 0,
        "lineas_body_con_texto": len([l for l in body.splitlines() if l.strip() and not l.strip().startswith("#")]),
        "runtime_imports_en_lock": len(re.findall(r"\{\{#runtime-import", lock_txt)),
        "roles_compilados": roles.group(1) if roles else "",
        "permisos_write_compilado": ", ".join(sorted(write_lock)),
        "version_compilador": meta.get("compiler_version", ""),
        "motor": meta.get("agent_id", ""),
        "registra_body_hash": "body_hash" in meta,
    }

    # Reglas -> brechas candidatas
    candidatas = {}

    declara_roles = "roles" in fm or "roles" in obtener_on(fm)
    menciona = re.search(r"maintainer|admin|owner|trusted|collaborator", texto_md, re.I)
    if roles and not declara_roles and menciona:
        candidatas["E1_roles"] = f"menciona '{menciona.group(0)}'; compilado exige: {roles.group(1)}"

    if '"APPROVE"' in lock_txt and "approv" not in texto_md.lower():
        candidatas["E2_aprobar"] = "allowed_events incluye APPROVE"

    if "cache-memory" in lock_txt and "cache-memory" not in texto_md:
        candidatas["E2_memoria"] = "cache-memory presente en el compilado"

    if activa_por_edicion(lock_yaml, lock_txt) and "edited" not in texto_md:
        candidatas["E2_edicion"] = "eventos con tipo 'edited'"

    if write_extra:
        candidatas["E2_escritura"] = "write en compilado: " + ", ".join(write_extra)

    if fm.get("imports") and body_solo_titulos(body):
        candidatas["E3_delegacion"] = f"{rasgos['n_imports']} imports; body solo con títulos"

    if isinstance(perms, dict) and perms.get("id-token") == "write" \
            and not re.search(r"id-token|oidc", body, re.I):
        candidatas["E4_idtoken"] = "id-token: write sin mención en el body"

    variantes = caso.get("variantes_mismos_imports")
    if isinstance(variantes, str) and variantes.strip():
        candidatas["E5_variantes"] = "mismos imports que: " + variantes

    return rasgos, candidatas


# ---------------------------------------------------------------------------
# Validación con los casos analizados a mano
# ---------------------------------------------------------------------------
def validar(resultados):
    print("\n=== Validación con casos analizados a mano ===")
    hubo = False
    for agente, candidatas in resultados:
        nombre = Path(agente).name
        if nombre not in ESPERADO:
            continue
        hubo = True
        esperado = ESPERADO[nombre]
        faltan = esperado - set(candidatas)
        sobran = set(candidatas) - esperado
        estado = "OK" if not faltan and not sobran else "REVISAR"
        print(f"[{estado}] {agente}")
        if faltan:
            print("   no detectadas:", ", ".join(sorted(faltan)))
        if sobran:
            print("   detectadas de más:", ", ".join(sorted(sobran)))
    if not hubo:
        print("No se encontraron los casos de validación en la muestra.")


def main():
    muestra = pd.read_csv(RAIZ / "datos" / "muestra.csv")
    DIR_RESULTADOS.mkdir(exist_ok=True)

    filas_agentes, filas_brechas, para_validar = [], [], []
    for _, caso in muestra.iterrows():
        rasgos, candidatas = analizar(caso)
        filas_agentes.append({**rasgos, "n_candidatas": len(candidatas)})
        para_validar.append((caso["path_md"], candidatas))
        for regla, detalle in candidatas.items():
            tipo, descripcion = REGLAS[regla]
            filas_brechas.append({
                "version_id": caso["version_id"],
                "repo": caso["repository_id"],
                "agente": caso["path_md"],
                "es_validacion": caso.get("es_validacion", False),
                "regla": regla,
                "tipo_sugerido": tipo,
                "descripcion": descripcion,
                "detalle": detalle,
                # Columnas para la revisión manual
                "confirmada": "",
                "tipo_final": "",
                "origen": "",
                "notas": "",
            })

    agentes = pd.DataFrame(filas_agentes)
    brechas = pd.DataFrame(filas_brechas, columns=[
        "version_id", "repo", "agente", "es_validacion", "regla", "tipo_sugerido",
        "descripcion", "detalle", "confirmada", "tipo_final", "origen", "notas"])

    agentes.to_csv(DIR_RESULTADOS / "agentes.csv", index=False)
    brechas.to_csv(DIR_RESULTADOS / "brechas_candidatas.csv", index=False)

    print(f"Agentes analizados: {len(agentes)}")
    print(f"YAML compilado no legible como estructura: {(~agentes['lock_legible_como_yaml']).sum()}")
    print(f"Brechas candidatas: {len(brechas)}")
    if len(brechas):
        print(brechas.groupby("regla").size().to_string())

    validar(para_validar)
    print(f"\nGuardado en {DIR_RESULTADOS}. Copia brechas_candidatas.csv como "
          f"brechas_revisadas.csv antes de revisar a mano.")


if __name__ == "__main__":
    main()
