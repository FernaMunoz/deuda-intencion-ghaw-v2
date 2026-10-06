"""
Paso 3: resumir la revisión manual.

Entrada : resultados/brechas_revisadas.csv (copia de brechas_candidatas.csv completada a mano)
          resultados/agentes.csv
Salida  : resultados/resumen_rq1.csv   agentes con al menos una brecha confirmada
          resultados/resumen_reglas.csv precisión de cada regla automática
          resultados/resumen_rq2_rq3.csv frecuencia por tipo y origen

Ejecutar desde la raíz del proyecto:
    python codigo/03_resumir.py

Columnas que se completan a mano en brechas_revisadas.csv:
    confirmada : si / no
    tipo_final : E1, E2, E3, E4, E5 o un tipo nuevo
    origen     : autor / imports / compilador (se pueden combinar con '+')
    notas      : justificación breve
Las brechas encontradas solo leyendo se agregan como filas nuevas con regla = manual.
"""

from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
DIR_RESULTADOS = RAIZ / "resultados"


def normalizar(valor):
    return str(valor).strip().lower() if pd.notna(valor) else ""


def main():
    ruta = DIR_RESULTADOS / "brechas_revisadas.csv"
    if not ruta.exists():
        print("Falta resultados/brechas_revisadas.csv.")
        print("Copia brechas_candidatas.csv con ese nombre y completa la revisión manual.")
        return

    brechas = pd.read_csv(ruta)
    agentes = pd.read_csv(DIR_RESULTADOS / "agentes.csv")

    # Los casos de validación se excluyen de los conteos del estudio
    agentes = agentes[~agentes["es_validacion"].astype(bool)]
    brechas = brechas[~brechas["es_validacion"].astype(bool)]

    brechas["confirmada_n"] = brechas["confirmada"].apply(normalizar)
    sin_revisar = (brechas["confirmada_n"] == "").sum()
    if sin_revisar:
        print(f"AVISO: {sin_revisar} filas sin revisar (columna 'confirmada' vacía).")

    confirmadas = brechas[brechas["confirmada_n"].isin(["si", "sí"])].copy()

    # RQ1: ¿cuántos agentes tienen al menos una brecha confirmada?
    con_brecha = confirmadas["version_id"].nunique()
    total = len(agentes)
    rq1 = pd.DataFrame([{
        "agentes_analizados": total,
        "agentes_con_brecha": con_brecha,
        "proporcion": round(con_brecha / total, 3) if total else 0,
    }])
    rq1.to_csv(DIR_RESULTADOS / "resumen_rq1.csv", index=False)

    # Precisión de las reglas automáticas (confirmadas / detectadas)
    auto = brechas[brechas["regla"] != "manual"]
    reglas = (auto.groupby("regla")
              .agg(detectadas=("regla", "size"),
                   confirmadas=("confirmada_n", lambda s: s.isin(["si", "sí"]).sum()))
              .reset_index())
    reglas["precision"] = (reglas["confirmadas"] / reglas["detectadas"]).round(3)
    reglas.to_csv(DIR_RESULTADOS / "resumen_reglas.csv", index=False)

    # RQ2 y RQ3: frecuencia por tipo y origen de las brechas confirmadas
    confirmadas["tipo_final"] = confirmadas["tipo_final"].fillna(confirmadas.get("tipo_sugerido"))
    confirmadas["origen"] = confirmadas["origen"].fillna("sin asignar")
    por_tipo = (confirmadas.groupby(["tipo_final", "origen"])
                .agg(brechas=("version_id", "size"), agentes=("version_id", "nunique"))
                .reset_index())
    por_tipo["agentes_%"] = (por_tipo["agentes"] / total * 100).round(1) if total else 0
    por_tipo.to_csv(DIR_RESULTADOS / "resumen_rq2_rq3.csv", index=False)

    print("\n=== RQ1 ===")
    print(rq1.to_string(index=False))
    print("\n=== Precisión de las reglas automáticas ===")
    print(reglas.to_string(index=False))
    print("\n=== RQ2 / RQ3: brechas confirmadas por tipo y origen ===")
    print(por_tipo.to_string(index=False))
    nuevas = (confirmadas["regla"] == "manual").sum()
    print(f"\nBrechas encontradas solo por revisión manual: {nuevas}")


if __name__ == "__main__":
    main()
