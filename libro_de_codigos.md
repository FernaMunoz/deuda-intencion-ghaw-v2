# Libro de códigos: brechas entre intención y compilación

## Definición de brecha

Una **brecha** es toda diferencia observable entre la intención que un agente declara en su archivo Markdown (frontmatter y body) y el comportamiento que habilita su archivo YAML compilado (`.lock.yml`). Existe cuando un elemento del YAML no puede rastrearse hasta el Markdown, o cuando lo rastreado lo contradice.

## Tipos de brecha

### E1. Discrepancia
- **Definición:** el Markdown declara una intención y el YAML implementa algo distinto.
- **Regla de asignación:** existe una afirmación explícita en el Markdown (descripción o body) que el YAML no respeta o amplía.
- **Ejemplo:** la descripción dice "explicit maintainer slash command", pero el YAML autoriza los roles `admin, maintainer, write`.
- **Regla automática:** `E1_roles` (candidata: siempre requiere revisión manual).

### E2. Omisión (capacidad no declarada)
- **Definición:** el YAML habilita capacidades que el Markdown no menciona.
- **Regla de asignación:** la capacidad está en el YAML y no aparece ni se infiere razonablemente desde el Markdown.
- **Ejemplos:** emitir una revisión `APPROVE`; memoria persistente (`cache-memory`); activarse al editar comentarios; permisos de escritura en jobs intermedios.
- **Reglas automáticas:** `E2_aprobar`, `E2_memoria`, `E2_edicion`, `E2_escritura`.

### E3. Delegación
- **Definición:** el body no contiene instrucciones propias y la intención se delega a archivos importados que se resuelven en tiempo de ejecución.
- **Regla de asignación:** se asigna solo si se cumplen ambas condiciones:
  - (a) el body no agrega instrucciones específicas del agente (solo títulos o vacío), y
  - (b) la intención delegada no es recuperable desde el Markdown ni desde el YAML (por ejemplo, el YAML solo contiene `{{#runtime-import ...}}`).
- **No se asigna** cuando el body agrega instrucciones propias, aunque use imports: eso es reutilización legítima.
- **Ejemplo:** `gh-aw-pr-rereview.md`, cuyo body es solo `# Internal PR Re-Review (Slash Command)`.
- **Regla automática:** `E3_delegacion` (verifica la condición a; la condición b se confirma manualmente).

### E4. Justificación ausente o invertida
- **Definición:** el Markdown declara un permiso o restricción sin explicar su propósito, o el propósito solo se recupera leyendo el YAML.
- **Regla de asignación:** el elemento es sensible (permisos de escritura, `id-token`, acceso de red amplio) y el body no explica para qué se usa.
- **Ejemplo:** `id-token: write` sin justificación; el YAML muestra que se usa para autenticación OIDC con Pulumi ESC.
- **Regla automática:** `E4_idtoken`.

### E5. Brecha entre agentes
- **Definición:** el propósito de un agente depende de otro del mismo repositorio sin que ninguno lo declare, o variantes de un mismo agente aplican restricciones distintas sin justificación.
- **Regla de asignación:** se comparan los agentes del mismo repositorio que comparten imports; se asigna si difieren en restricciones o capacidades sin explicación, o si uno cubre un caso que el otro omite sin declararlo.
- **Ejemplo:** `gh-aw-pr-review` excluye PRs de forks y `gh-aw-pr-rereview` no, sin explicar la diferencia.
- **Regla automática:** `E5_variantes` (solo identifica agentes comparables; la brecha se confirma manualmente).

### Tipos nuevos
Si durante la revisión aparece una brecha que no encaja en E1–E5, se registra con `regla = manual`, se describe en `notas` y se le asigna un código provisional (E6, E7…). Un tipo nuevo se incorpora al libro de códigos si aparece en más de un caso.

## Origen de la brecha

| Valor | Cuándo usarlo |
|---|---|
| `autor` | La brecha se debe a lo que escribió (u omitió) el autor del Markdown |
| `imports` | La capacidad o instrucción proviene de un archivo importado |
| `compilador` | Proviene de un valor por defecto del compilador de gh-aw |

Si el origen no puede determinarse con certeza (por ejemplo, porque los archivos importados no están en el dataset), se registra la mejor inferencia y se indica "(inferido)" en `notas`. Se pueden combinar orígenes con `+`.

## Qué NO es una brecha

No se registran como brechas los elementos de infraestructura que el compilador agrega de forma uniforme a todos los agentes y que no amplían sus capacidades: instalación de dependencias, registro de trazas, fijación de versiones de acciones, redacción de secretos en logs, carga de artefactos.

## Procedimiento de revisión

1. Copiar `resultados/brechas_candidatas.csv` como `resultados/brechas_revisadas.csv`.
2. Para cada fila, abrir los archivos en `casos/<version_id>/` y decidir:
   - `confirmada`: `si` o `no`
   - `tipo_final`: E1–E5 o un tipo nuevo
   - `origen`: autor, imports o compilador
   - `notas`: justificación breve
3. Leer el Markdown completo y agregar como filas nuevas (`regla = manual`) las brechas que las reglas no detectaron.

## Consistencia

Para evaluar la consistencia de la clasificación se usará una de estas opciones (indicar cuál en el informe):
- **Segundo codificador:** otra persona clasifica un subconjunto de casos y se calcula el acuerdo (kappa de Cohen).
- **Recodificación:** la misma investigadora vuelve a clasificar el subconjunto una o dos semanas después y se compara el resultado.
