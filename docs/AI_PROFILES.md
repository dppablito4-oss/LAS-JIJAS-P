# Perfiles de IA

Configuración verificada el **29/10/2026** en documentación oficial. Los IDs se configuran en servidor; nunca se exponen claves en frontend, capacidades o informes. Cambiar `.env` requiere reiniciar. No se ejecutaron llamadas de IA facturables durante la implementación.

## Actualización: perfil hybrid con revisión

El `.env` local está adaptado a `APP_MODE=real`, `AI_PROFILE=hybrid`, conservando exactamente ambos valores de claves anteriores. La suite actual tiene **40 tests aprobados**; la descripción de 30 pruebas de la implementación anterior se conserva más abajo como historial.

```dotenv
AI_PROFILE=hybrid
OPENAI_VISION_MODEL=gpt-6-luna
OPENAI_VISION_EFFORT=low
OPENAI_REVIEW_MODEL=gpt-6.1-sol
OPENAI_REVIEW_ENABLED=true
OPENAI_REVIEW_EFFORT=high
OPENAI_REVIEW_MODE=standard
DEEPSEEK_MODEL=deepseek-v4-pro
DEEPSEEK_THINKING=true
DEEPSEEK_REASONING_EFFORT=high
```

Recorrido: Luna extrae, DeepSeek analiza con herramientas y Sol revisa el informe y el comentario. La revisión recibe evidencia y limitaciones; no tiene herramientas ni puede escribir en el motor de probabilidades. Se guarda por separado y aparece como «Revisión adicional» en la web. Un fallo, JSON inválido o timeout se declara sin borrar el informe principal. El uso conocido de la revisión se registra en `api_usage` aun si una validación posterior falla.

`OPENAI_REVIEW_ENABLED` es el interruptor explícito de revisión en cualquier perfil. Para recuperar la configuración ahorradora cambia también `DEEPSEEK_MODEL=deepseek-flash` y `OPENAI_REVIEW_ENABLED=false`; cambiar solo `AI_PROFILE` no sustituye los modelos personalizados ni apaga un interruptor habilitado.

`OPENAI_REVIEW_MODE=pro` es un **preset local de esta aplicación**: usa `reasoning.effort=max` con el mismo `gpt-6.1-sol`, sin ampliar automáticamente el límite de tokens ni el plazo. No es otro modelo, una suscripción Pro ni una modalidad comercial de la API. `standard` respeta `OPENAI_REVIEW_EFFORT=high`. OpenAI documenta [los esfuerzos admitidos por Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol).

Límites configurados y aplicados:

- `VISION_MAX_TOKENS=4096`, `DEEPSEEK_MAX_TOKENS=8192`, `REVIEW_MAX_TOKENS=8192`: por respuesta, incluido razonamiento cuando corresponde. `MAX_OUTPUT_TOKENS=8192` es el respaldo si una etapa no tiene límite propio y el límite del analista Sol en perfil sol.
- `MODEL_TIMEOUT_SECONDS=45`: plazo máximo de cada petición IA, además del timeout del SDK; también limita la espera del ajuste estadístico. `AI_TIMEOUT_SECONDS=90`: presupuesto conjunto para todas las rondas de análisis y la revisión; se aplica separadamente como plazo externo de extracción.
- `MAX_ANALYSIS_SECONDS=240`: máximo del trabajo completo, incluidas consultas deportivas. La revisión solo recibe el tiempo IA restante; seis rondas no garantizan seis peticiones completas de 45 segundos.
- `MAX_HISTORY_AGE_DAYS=30`: si el último resultado disponible es más antiguo, se conservan las estadísticas descriptivas pero se omite la predicción. No recorta el entrenamiento a 30 días.
- `MAX_QUOTE_AGE_HOURS=24`: una cuota más antigua, o con hora futura por más de cinco minutos, conserva su probabilidad implícita y queda sin EV. Es necesario corregir la observación con una cuota realmente revisada.

`DEEPSEEK_THINKING=false` desactiva thinking explícitamente y omite `reasoning_effort` en la petición. Ningún límite equivale a un presupuesto monetario. Al activar revisión, el coste total se muestra desconocido para evitar confundir el coste del analista con el de ambas etapas. `analyst_estimated_cost_usd` mantiene la estimación del analista si su tarifa está configurada; la revisión conserva su uso bruto y coste desconocido.

Las nuevas pruebas cubren lectura de la plantilla híbrida, presets standard/pro, revisión desactivada sin llamadas, conservación de probabilidades/EV, fallo de revisión sin pérdida del informe, cuotas antiguas/futuras, históricos antiguos, thinking desactivado y cancelación de peticiones por timeout. Todas son offline con claves de prueba; no se probó consumo real.

## Sol: un modelo para las dos tareas

```dotenv
APP_MODE=real
AI_PROFILE=sol
OPENAI_API_KEY=tu_clave_local
OPENAI_SINGLE_MODEL=gpt-6.1-sol
OPENAI_ANALYSIS_EFFORT=medium
```

`gpt-6.1-sol` lee la captura y coordina el análisis con las herramientas deportivas permitidas. Es un solo ID de modelo, pero son solicitudes separadas: extracción, análisis y rondas de herramientas. Este perfil solo requiere clave OpenAI. Ignora `OPENAI_VISION_MODEL` y la clave/modelo DeepSeek.

La [ficha oficial de GPT-6.1 Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol) confirma entrada de imagen y texto. Las herramientas requieren **Responses API**, implementada para el analista. Se conservan las salidas de razonamiento cifradas en memoria para las rondas siguientes, con `store=false`, sin guardar razonamiento en SQLite. Visión usa esfuerzo low; el análisis, medium configurable.

## Economy: visión Luna y análisis DeepSeek

```dotenv
APP_MODE=real
AI_PROFILE=economy
OPENAI_API_KEY=tu_clave_local_openai
OPENAI_VISION_MODEL=gpt-6-luna
DEEPSEEK_API_KEY=tu_clave_local_deepseek
DEEPSEEK_MODEL=deepseek-flash
DEEPSEEK_REASONING_EFFORT=high
```

[GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna) admite imágenes y está orientado a tareas de gran volumen con menor coste. Aquí solo extrae el ticket; DeepSeek coordina el análisis, con thinking habilitado y esfuerzo high. Las claves se usan según la tarea: una entrada manual puede analizarse con DeepSeek sin clave OpenAI.

El catálogo vigente de [DeepSeek Models & Pricing](https://api-docs.deepseek.com/quick_start/pricing/) presenta:

- `deepseek-flash`: versión servida **DeepSeek-V4.1-Flash-1017**. Es la opción predeterminada para ahorro; admite razonamiento y herramientas.
- `deepseek-v4-pro`: versión servida **DeepSeek-V4-Pro-0813**. Alternativa disponible, con razonamiento y herramientas; su tarifa publicada es mayor. Para elegirla cambia únicamente `DEEPSEEK_MODEL`.

No se verificó un ID `deepseek-v4.1-pro`. Tampoco se usa R1/deepseek-reasoner como selección actual: el [historial oficial](https://api-docs.deepseek.com/updates/) documenta su sustitución por modelos posteriores y la retirada anunciada de los nombres legacy. El nombre Pro por sí solo no permite concluir que supera al Flash más reciente en esta aplicación; no hay benchmark deportivo propio de los LLM.

La [actualización oficial del 17/10/2026](https://api-docs.deepseek.com/updates/#deepseek-v41-flash-1017-update) identifica Flash-1017 como revisión más reciente de Flash. La selección favorece su generación actual, thinking y coste; no promete que maximice exactitud para todos los casos.

## Límites y validación

El `.env` local quedó con `AI_PROFILE=sol`; se conservaron valores de claves y el modo demo/real existente. `.env.example` contiene los dos modelos y comentarios, sin credenciales. `env_ignore_empty=true` permite que tarifas opcionales vacías se interpreten como no configuradas.

Ambos analistas comparten validación de herramientas, deduplicación, máximo 12 llamadas por ronda, límite de concurrencia y 6 rondas. Ninguno cambia probabilidades del motor estadístico. No hay cambio de modelo automático. Los informes nuevos conservan perfil, proveedor y modelo; los originales no se modifican.

**30 tests offline aprobados**, incluidas cinco pruebas nuevas de perfiles: selección/configuración y tarifas vacías, visión de ambos perfiles, Responses Sol con continuidad de razonamiento/IDs, DeepSeek thinking con IDs y respuesta incompleta con uso conservado. El frontend compila con tipos. El acceso real de la cuenta y la calidad con imágenes reales siguen pendientes de prueba con credenciales configuradas; no se infieren a partir de estos mocks.

El coste estimado del analista solo se calcula con tarifas fechadas cuyo `PRICE_MODEL` coincide con el modelo activo. Cambiar a Sol o Pro no reutiliza por error una tarifa de Flash. El coste de extracción sigue separado; no hay factura total ni cálculo completo de caché/franja horaria. Consulta siempre los precios vigentes de cada proveedor.
