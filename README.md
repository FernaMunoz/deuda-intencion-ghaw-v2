# La brecha entre intención y compilación: Un estudio exploratorio de la Deuda de Intención en GitHub Agentic Workflows

Paquete de réplica **parcial (Etapa 2)** del estudio que caracteriza la deuda de intención en agentes definidos con GitHub Agentic Workflows (gh-aw), comparando el archivo Markdown de cada agente con el YAML compilado que GitHub Actions ejecuta.

- **Autora:** Fernanda Muñoz Pinochet, Universidad de La Frontera
- **Versión del repositorio:** `etapa2` 
- **DOI Zenodo:** 10.5281/zenodo.23176382 (https://doi.org/10.5281/zenodo.23176382)

## Preguntas de investigación

- **RQ1:** ¿Existe una brecha identificable entre la intención especificada en el Markdown y el comportamiento que el agente puede ejecutar una vez compilado a YAML?
- **RQ2:** ¿Qué tipos de deuda de intención pueden caracterizarse a partir de esta brecha?
- **RQ3:** ¿Con qué frecuencia se presenta cada tipo?

## Método en una línea

Detección automática de brechas candidatas mediante reglas, seguida de validación y codificación manual con un libro de códigos (`libro_de_codigos.md`).

## Organización

```
deuda-intencion-ghaw/
├── README.md                 este archivo
├── requirements.txt          dependencias de Python
├── libro_de_codigos.md       tipos de brecha, reglas de asignación y procedimiento
├── codigo/
│   ├── 01_cargar_y_unir.py   descarga, une .md con .lock.yml, selecciona la muestra
│   ├── 02_detectar_brechas.py aplica las reglas y genera las brechas candidatas
│   └── 03_resumir.py         resume la revisión manual (RQ1, RQ2, RQ3)
├── datos/
│   ├── fuente.md             origen, versión, fecha y criterios de selección
│   ├── muestra.csv           agentes seleccionados (generado por el paso 1)
│   ├── resumen_dataset.csv   totales del dataset (agentes, repositorios, imports)
│   ├── agentes_mas_frecuentes.csv  nombres de agente más repetidos y su porcentaje
│   └── plantillas_replicadas.csv   plantillas presentes en más de un repositorio
├── casos/<version_id>/       agente.md, frontmatter.yml, body.md, compilado.lock.yml
└── resultados/
    ├── agentes.csv           rasgos extraídos de cada agente
    ├── brechas_candidatas.csv salida automática (se sobrescribe al ejecutar el paso 2)
    ├── brechas_revisadas.csv  revisión manual (copia completada a mano)
    ├── resumen_rq1.csv
    ├── resumen_reglas.csv
    └── resumen_rq2_rq3.csv
```

## Preparar el entorno

Requiere Python 3.10 o superior.

```bash
python -m venv .venv
source .venv/bin/activate        # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

También puede ejecutarse en Google Colab: subir la carpeta, ejecutar `!pip install -r requirements.txt` y luego los scripts con `!python codigo/...`.

## Reproducir los resultados

Todos los comandos se ejecutan desde la raíz del proyecto.

**Opción A: desde los datos conservados (recomendada).** El paquete incluye `datos/muestra.csv` y la carpeta `casos/`, por lo que no es necesario volver a descargar el dataset:

```bash
python codigo/02_detectar_brechas.py
python codigo/03_resumir.py
```

**Opción B: desde cero.** Descarga el dataset y vuelve a generar la muestra (requiere conexión a Hugging Face):

```bash
python codigo/01_cargar_y_unir.py
python codigo/02_detectar_brechas.py
# revisión manual: copiar brechas_candidatas.csv como brechas_revisadas.csv y completarla
python codigo/03_resumir.py
```

El paso 2 imprime además una **validación**: compara las brechas detectadas en `gh-aw-pr-review.md` y `gh-aw-pr-rereview.md` con las identificadas manualmente en el análisis exploratorio.

## Resultados por pregunta

| Pregunta | Archivo | Contenido |
|---|---|---|
| RQ1 | `resultados/resumen_rq1.csv` | Agentes analizados, agentes con al menos una brecha confirmada y proporción |
| RQ2 | `resultados/resumen_rq2_rq3.csv` | Tipos de brecha confirmados y su origen |
| RQ3 | `resultados/resumen_rq2_rq3.csv` | Cantidad de brechas y porcentaje de agentes por tipo |
| Procedimiento | `resultados/resumen_reglas.csv` | Precisión de cada regla automática (confirmadas / detectadas) |

## Estado del estudio

**Implementado**
- Descarga y unión de las tablas del dataset.
- Selección de muestra con criterios documentados y semilla fija.
- Reglas automáticas para E1 (candidata), E2, E3, E4 y E5 (candidata).
- Validación de las reglas con los dos casos analizados a mano.
- Resumen de la revisión manual.

**Pendiente**
- Revisión manual completa de la muestra preliminar.
- Evaluación de consistencia de la clasificación.
- Ampliación de la muestra para el estudio completo.
- Análisis de la evolución entre versiones de un mismo agente.

## Limitaciones conocidas

- Los archivos importados (`imports`) no están en el dataset; el origen de algunas brechas es inferido.
- Las reglas automáticas son deliberadamente simples y pueden producir falsos positivos; por eso toda brecha candidata se confirma a mano.
- Si un lock file no puede leerse como YAML, las reglas usan búsqueda de texto (columna `lock_legible_como_yaml` en `agentes.csv`).

## Licencia

MIT
