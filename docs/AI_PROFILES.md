# Perfiles de IA

Configuración verificada el **29/10/2026** en documentación oficial. Los IDs se configuran en servidor; nunca se exponen claves en frontend, capacidades o informes. Cambiar `.env` requiere reiniciar. No se ejecutaron llamadas de IA facturables durante la implementación.

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
