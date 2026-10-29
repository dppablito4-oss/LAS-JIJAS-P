# Arquitectura y decisiones

Una SPA React llama al backend FastAPI. Vite actúa de proxy durante desarrollo; la compilación se sirve desde FastAPI en la ejecución integrada. Todo queda en localhost por defecto. Sin Redis, MCP obligatorio, servicios externos propios, pagos ni cuentas multiusuario.

El demo usa un reloj de análisis simulado fijo (29/10/2026 12:00 UTC) para que sus eventos ficticios sigan siendo reproducibles. Los trabajos e instantes de descarga conservan el reloj real. El modo real siempre usa el reloj UTC actual.

## Recorrido

1. Captura validada y normalizada en memoria, o formulario. El extractor OpenAI devuelve JSON Pydantic; demo devuelve una selección simulada rotulada. Toda extracción requiere revisión.
2. El usuario edita datos y elige un evento de candidatos. Identidad incluye deporte, competición masculina profesional/NBA, temporada, inicio UTC e IDs nativos. Consulta por competición y tres días UTC alrededor de la fecha introducida para cubrir el cambio de día de Lima. Se muestra elección explícita; no se elige una coincidencia por nombre en silencio.
3. `POST /api/analyses` valida revisión y campos, inserta un trabajo y una clave única en SQLite. Idempotencia usa hash de contenido normalizado explícito; defaults temporales generados no alteran la identidad de reintentos idénticos.
4. Un worker asyncio consume la cola local de hasta 25 trabajos. Guarda estados queued/running/completed/failed/interrupted. Reinicio marca pendientes como interrumpidos. No reintenta gasto automáticamente.
5. Se vuelve a validar que el ID confirmado está entre los candidatos. Solo eventos futuros se modelan. Calendarios y muestras históricas se cachean por proveedor/temporada/parámetros/corte; originales de la fuente están disponibles en SQLite local.
6. Python calcula forma, precios y Dixon-Coles cuando hay muestra suficiente. El corte es la hora UTC de inicio del análisis, anterior al evento; no el horario de extracción ni el de cierre. Nunca se usan resultados futuros o cuotas de cierre como entrada.
7. Los perfiles Sol (Responses) y Economy (DeepSeek thinking) comparten el catálogo permitido. El catálogo de herramientas expone solo siete funciones de lectura/cálculo por índice de selección. Pydantic rechaza argumentos adicionales, ventanas inválidas, herramientas ajenas e índices fuera de rango. DeepSeek recibe solo herramientas pertinentes, respuestas pequeñas y hechos calculados. El ciclo conserva IDs, valida, deduplica y devuelve resultados antes de seguir. Hasta 6 rondas, 12 llamadas por ronda, 3 concurrentes y 1.800 tokens por respuesta.
8. El informe determinista separa evento, cálculos, evidencia y ausencias. DeepSeek agrega un comentario claramente separado; no sustituye probabilidades, EV ni conclusión. El servicio persiste el informe, sin delegar la escritura a la IA.

## Módulos

- `schemas.py`: contratos de selección, evento, evidencia, extracción y solicitud.
- `providers.py`: demo sintético, ESPN específico por liga, sports-skills fútbol y nba_api.
- `isolated.py`: catálogo cerrado de tres operaciones SDK en procesos terminables. Sin ejecución de comandos ni imports de usuario.
- `analytics.py`: reglas de mercado, forma y dependencias/incompatibilidades.
- `model.py`: importación diferida de penaltyblog, ajuste ponderado, distribución y evaluación temporal.
- `tools.py`: catálogo permitido, esquemas estrictos y memoización.
- `llm.py`: imagen, visión OpenAI y ciclo de herramientas DeepSeek con reasoning en memoria.
- `db.py`: trabajos inmutables una vez completados, caché y registros de uso de API.
- `service.py`: orquestación, límites y persistencia.
- `main.py`: API, CORS, comprobación de origen/host y frontend estático.

## Estado, costes y retención

SQLite conserva solicitudes, informes, timestamps, relación `parent_id`, uso de API y caché. Cada revisión genera un ID nuevo; no se sobreescribe el informe previo al encuentro. No hay actualización automática de resultados finales todavía: `final_result` es null y no se inventa. El historial muestra los mercados/cuotas y permite exportar evidencia.

`api_usage` persiste cada respuesta devuelta por la API, antes del parseo o ronda siguiente; así los fallos posteriores no borran uso conocido. `GET /analyses/{id}` devuelve también `api_usage`, incluso si el informe falla. No se puede registrar una respuesta que el proveedor nunca llegó a devolver; gasto exacto ante cortes de red queda desconocido. Se deshabilitan reintentos automáticos del SDK. El precio configurable/fechado del analista exige PRICE_MODEL coincidente con el modelo activo; no incluye extracción ni factura de cuenta.

No se persisten imágenes ni razonamiento; sí el texto revisado que el usuario pide conservar en el historial. Acceso HTTP sin logs de petición por defecto en scripts. CORS y Origin restringidos a localhost:8000/5173, hosts localhost/127.0.0.1; `testserver` solo permite el cliente de pruebas. No se usa autenticación: es una aplicación local personal, no un servicio multiusuario. No exponer el puerto a internet.

La caché conserva el sello original de descarga y los datos originales; un hit no actualiza artificialmente la fecha de descarga. `as_of` histórico representa el último dato con disponibilidad conservadora. TTL 300/3.600/21.600 segundos para calendarios/NBA/fútbol. No se reconstruyen noticias o resultados de eventos pasados a partir de caché actual. Retención indefinida hasta borrado local; la limpieza automática queda pendiente.

## Incertidumbres deliberadas

Modelo siempre experimental; evaluación pequeña, sin optimización de rentabilidad. No se ajustan probabilidades con lesiones o xG inventados. No se multiplican selecciones; incompatibilidades 1X2 y totales del mismo evento se detectan. NBA solo descriptivo y cuota implícita. Sin fuentes comprobadas de bajas, se declara ausencia de cobertura.

Los wrappers deportivos pueden cambiar o fallar. Los adaptadores devuelven parcial/unavailable y conservan el fallo; los procesos externos se terminan tras timeout. El límite global de análisis protege la interfaz; una combinación de muchas selecciones y fuentes lentas puede finalizar en failed en vez de producir un informe parcial completo. La concurrencia de workers y una cola distribuida quedan fuera del MVP.
