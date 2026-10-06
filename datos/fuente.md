# Fuente de los datos

Completar antes de la entrega. La pauta exige documentar cómo se obtuvieron los datos.

| Campo | Valor |
|---|---|
| Dataset | GHAW-H (`pavtch/GHAW-H`), https://huggingface.co/datasets/pavtch/GHAW-H |
| Versión del dataset (commit) | _completar: pestaña "Files and versions" del dataset_ |
| Fecha de descarga | _completar_ |
| Tablas utilizadas | `source_markdown_file_snapshot`, `source_markdown_file_version`, `lock_file_snapshot` |
| Herramienta | `codigo/01_cargar_y_unir.py` (biblioteca `datasets` de Hugging Face) |

## Unión de las tablas

Cada Markdown se une con su lock file compilado a través de la tabla de versiones:

```
source_markdown_file_snapshot --(source_markdown_file_snapshot_id)--> source_markdown_file_version
source_markdown_file_version  --(source_markdown_file_version_id)---> lock_file_snapshot
```

## Transformaciones y criterios de selección

1. Se descartan los pares cuyo Markdown o lock file tiene contenido vacío.
2. Se conserva solo la última versión de cada agente (versiones sin sucesora), para evitar contar varias veces snapshots casi idénticos del mismo archivo.
3. Se desordenan los agentes con semilla fija (42) y se toman como máximo 2 por repositorio, para que ningún repositorio domine la muestra.
4. De ese conjunto se seleccionan 20 agentes al azar (misma semilla).
5. Se agrega un único caso de validación por cada agente analizado a mano (`gh-aw-pr-review.md` y `gh-aw-pr-rereview.md`), solo si ese agente no quedó en la muestra aleatoria.
6. Opcional (`UNA_POR_PLANTILLA = True`): antes de muestrear, se deja una sola copia de cada plantilla replicada, identificada por el campo `source:` del frontmatter o, si no existe, por nombre de archivo y contenido idéntico. Evita que una plantilla instalada en muchos repositorios domine la muestra.

Los valores de los puntos 3, 4 y 6 están al inicio de `codigo/01_cargar_y_unir.py`.

**Nota sobre la primera ejecución:** una versión anterior del script agregaba como casos de validación todas las copias de `gh-aw-pr-review.md` y `gh-aw-pr-rereview.md` del dataset (89 agentes adicionales a los 20 aleatorios). Esos casos quedaban marcados con `es_validacion = True` y se excluían de los conteos, pero inflaban la muestra. Se corrigió para agregar un solo caso por nombre.

## Datos conservados

- `datos/muestra.csv`: identificadores y metadatos de los agentes seleccionados.
- `casos/<version_id>/`: los archivos de cada agente (`agente.md`, `frontmatter.yml`, `body.md`, `compilado.lock.yml`).

Con estos archivos el análisis (pasos 2 y 3) puede ejecutarse sin volver a descargar el dataset.
