"""
Paso 1: cargar el dataset GHAW-H, unir cada Markdown con su lock file,
seleccionar la muestra y guardar los casos en disco.

Entrada : dataset pavtch/GHAW-H en Hugging Face
Salida  : datos/muestra.csv
          casos/<version_id>/  (agente.md, frontmatter.yml, body.md, compilado.lock.yml)

Ejecutar desde la raíz del proyecto:
    python codigo/01_cargar_y_unir.py
"""

from pathlib import Path

import pandas as pd
import yaml

# ---------------------------------------------------------------------------
# Configuración (registrar estos valores en datos/fuente.md)
# ---------------------------------------------------------------------------
DATASET = "pavtch/GHAW-H"
REVISION = None          # Reemplazar por el commit del dataset (pestaña "Files and versions")
MAX_POR_REPO = 2         # Máximo de agentes por repositorio en la muestra
TAMANO_MUESTRA = 20      # Cantidad de agentes de la muestra
SEMILLA = 42             # Semilla para que la muestra sea siempre la misma
UNA_POR_PLANTILLA = False  # True: cada plantilla replicada (mismo 'source' o contenido) cuenta una sola vez

# Casos analizados a mano, usados para validar las reglas (paso 2)
CASOS_VALIDACION = [
    "gh-aw-pr-review.md",
    "gh-aw-pr-rereview.md",
    "doc-bot.md",
    "auto-triage.md",
    "daily-repo-status.md",
    "malicious-code-scan.md",
    "markdown-linter.md",
    "documentation.md",
]

RAIZ = Path(__file__).resolve().parent.parent
DIR_DATOS = RAIZ / "datos"
DIR_CASOS = RAIZ / "casos"


def cargar(subset):
    """Descarga una tabla (subset) del dataset como DataFrame de pandas."""
    from datasets import load_dataset
    ds = load_dataset(DATASET, subset, split="data", revision=REVISION)
    return ds.to_pandas()


def unir(md, ver, lock):
    """Une Markdown -> versión -> lock file. Cada fila resultante es un par."""
    pares = (ver
             .merge(md, on="source_markdown_file_snapshot_id")
             .merge(lock, on="source_markdown_file_version_id",
                    suffixes=("_md", "_lock")))
    return pares


def limpiar(pares):
    """Descarta pares incompletos y deja solo la última versión de cada agente."""
    total = len(pares)
    pares = pares[pares["content_md"].fillna("").str.strip().astype(bool)]
    pares = pares[pares["content_lock"].fillna("").str.strip().astype(bool)]
    sin_contenido = total - len(pares)

    # La última versión de cada agente es la que no tiene sucesora
    ultimos = pares[pares["successor_source_markdown_file_version_id"].isna()].copy()

    print(f"Pares totales: {total}")
    print(f"Pares descartados por contenido vacío: {sin_contenido}")
    print(f"Agentes distintos (última versión): {len(ultimos)}")
    return ultimos


def lista_imports(frontmatter):
    """Devuelve la lista de imports declarados en el frontmatter (vacía si no hay)."""
    try:
        fm = yaml.safe_load(frontmatter or "") or {}
    except yaml.YAMLError:
        return []
    imports = fm.get("imports") if isinstance(fm, dict) else None
    if not isinstance(imports, list):
        return []
    return sorted(str(i) for i in imports)


def agregar_variantes(ultimos):
    """Para cada agente, lista otros agentes del mismo repositorio con los mismos imports.
    Sirve para detectar candidatos a brecha entre agentes (E5)."""
    ultimos = ultimos.copy()
    ultimos["imports"] = ultimos["frontmatter"].apply(lista_imports)
    ultimos["clave_imports"] = ultimos["imports"].apply(lambda l: "|".join(l))

    variantes = []
    for _, fila in ultimos.iterrows():
        if not fila["clave_imports"]:
            variantes.append("")
            continue
        mismos = ultimos[(ultimos["repository_id"] == fila["repository_id"])
                         & (ultimos["clave_imports"] == fila["clave_imports"])
                         & (ultimos["path_md"] != fila["path_md"])]
        variantes.append(";".join(sorted(mismos["path_md"].unique())))
    ultimos["variantes_mismos_imports"] = variantes
    return ultimos


def campo_source(frontmatter):
    """Devuelve la plantilla de origen declarada en 'source:' (sin el commit), o ''."""
    try:
        fm = yaml.safe_load(frontmatter or "") or {}
    except yaml.YAMLError:
        return ""
    src = fm.get("source") if isinstance(fm, dict) else None
    return str(src).split("@")[0] if src else ""


def agregar_plantillas(ultimos):
    """Identifica agentes replicados: misma plantilla de origen ('source:') o, si no la
    declaran, mismo nombre de archivo con contenido idéntico. Cuenta en cuántos
    repositorios aparece cada plantilla."""
    ultimos = ultimos.copy()
    ultimos["source"] = ultimos["frontmatter"].apply(campo_source)
    ultimos["contenido_hash"] = pd.util.hash_pandas_object(
        ultimos["content_md"].fillna(""), index=False).astype(str)
    ultimos["plantilla"] = ultimos.apply(
        lambda f: f["source"] if f["source"] else f"{f['path_md']}#{f['contenido_hash']}", axis=1)
    ultimos["repos_misma_plantilla"] = ultimos.groupby("plantilla")["repository_id"].transform("nunique")
    return ultimos


def resumen_dataset(ultimos):
    """Guarda una caracterización del dataset (sección IV-A del informe)."""
    DIR_DATOS.mkdir(exist_ok=True)
    total = len(ultimos)
    filas = [
        ("agentes_distintos_ultima_version", total),
        ("repositorios_distintos", ultimos["repository_id"].nunique()),
        ("nombres_de_archivo_distintos", ultimos["path_md"].nunique()),
        ("agentes_con_source_declarado", int((ultimos["source"] != "").sum())),
        ("agentes_con_imports", int(ultimos["imports"].apply(bool).sum())),
    ]
    pd.DataFrame(filas, columns=["indicador", "valor"]).to_csv(
        DIR_DATOS / "resumen_dataset.csv", index=False)

    top_nombres = (ultimos["path_md"].value_counts().head(15)
                   .rename_axis("agente").reset_index(name="n_agentes"))
    top_nombres["porcentaje"] = (top_nombres["n_agentes"] / total * 100).round(1)
    top_nombres.to_csv(DIR_DATOS / "agentes_mas_frecuentes.csv", index=False)

    plantillas = (ultimos.groupby("plantilla")
                  .agg(n_agentes=("plantilla", "size"),
                       n_repositorios=("repository_id", "nunique"),
                       ejemplo=("path_md", "first"))
                  .sort_values("n_agentes", ascending=False)
                  .reset_index())
    plantillas = plantillas[plantillas["n_repositorios"] > 1]
    plantillas.to_csv(DIR_DATOS / "plantillas_replicadas.csv", index=False)

    print("\n=== Caracterización del dataset ===")
    for k, v in filas:
        print(f"{k}: {v}")
    print("\nAgentes más frecuentes:")
    print(top_nombres.head(10).to_string(index=False))
    print(f"\nPlantillas presentes en más de un repositorio: {len(plantillas)}")


def seleccionar(ultimos):
    """Muestra aleatoria con tope por repositorio, más los casos de validación."""
    base = ultimos.sample(frac=1, random_state=SEMILLA)
    if UNA_POR_PLANTILLA:
        base = base.drop_duplicates("plantilla")
        print(f"Agentes tras dejar una copia por plantilla: {len(base)}")
    # Se desordena y se toman hasta MAX_POR_REPO agentes de cada repositorio
    por_repo = (base
                .groupby("repository_id")
                .head(MAX_POR_REPO))
    muestra = por_repo.sample(min(len(por_repo), TAMANO_MUESTRA), random_state=SEMILLA)
    muestra = muestra.assign(es_validacion=False)

    # Casos de validación: UN solo agente por nombre (el primero por id), y solo si
    # ese nombre no quedó ya en la muestra aleatoria.
    validacion = []
    for caso in CASOS_VALIDACION:
        if isinstance(caso, int):  # un version_id exacto
            candidatos = ultimos[ultimos["source_markdown_file_version_id"] == caso]
            ya_esta = muestra["source_markdown_file_version_id"].eq(caso).any()
        else:                      # un nombre de archivo
            candidatos = ultimos[ultimos["path_md"].astype(str).str.endswith("/" + caso)]
            ya_esta = muestra["path_md"].astype(str).str.endswith("/" + caso).any()
        if not ya_esta and len(candidatos):
            validacion.append(candidatos.sort_values("source_markdown_file_version_id").head(1))
    validacion = (pd.concat(validacion).assign(es_validacion=True)
                  if validacion else ultimos.head(0).assign(es_validacion=True))

    final = pd.concat([muestra, validacion], ignore_index=True)
    print(f"Agentes en la muestra: {len(muestra)} | casos de validación: {len(validacion)}")
    return final


def guardar(muestra):
    """Guarda muestra.csv (solo metadatos) y los archivos de cada caso."""
    DIR_DATOS.mkdir(exist_ok=True)
    DIR_CASOS.mkdir(exist_ok=True)

    for _, f in muestra.iterrows():
        carpeta = DIR_CASOS / str(f["source_markdown_file_version_id"])
        carpeta.mkdir(exist_ok=True)
        (carpeta / "agente.md").write_text(f["content_md"] or "", encoding="utf-8")
        (carpeta / "frontmatter.yml").write_text(f["frontmatter"] or "", encoding="utf-8")
        (carpeta / "body.md").write_text(f["body"] or "", encoding="utf-8")
        (carpeta / "compilado.lock.yml").write_text(f["content_lock"] or "", encoding="utf-8")

    columnas = ["source_markdown_file_version_id", "source_markdown_file_snapshot_id",
                "lock_file_snapshot_id", "repository_id", "path_md", "path_lock",
                "commit_sha", "committed_at", "rank", "variantes_mismos_imports",
                "source", "repos_misma_plantilla", "es_validacion"]
    columnas = [c for c in columnas if c in muestra.columns]
    muestra[columnas].rename(columns={"source_markdown_file_version_id": "version_id"}) \
        .to_csv(DIR_DATOS / "muestra.csv", index=False)
    print(f"Guardado: {DIR_DATOS / 'muestra.csv'} y {len(muestra)} carpetas en {DIR_CASOS}")


def main():
    md = cargar("source_markdown_file_snapshot")
    ver = cargar("source_markdown_file_version")
    lock = cargar("lock_file_snapshot")

    pares = unir(md, ver, lock)
    ultimos = limpiar(pares)
    ultimos = agregar_variantes(ultimos)
    ultimos = agregar_plantillas(ultimos)
    resumen_dataset(ultimos)
    muestra = seleccionar(ultimos)

    # Comprobación de sangría: si el YAML no tiene líneas indentadas, avisar
    ejemplo = muestra.iloc[0]["content_lock"]
    if not any(l.startswith("  ") for l in ejemplo.splitlines()):
        print("AVISO: el lock file de ejemplo no tiene sangría. "
              "Las reglas usarán búsqueda de texto en lugar de leer la estructura YAML.")

    guardar(muestra)


if __name__ == "__main__":
    main()
