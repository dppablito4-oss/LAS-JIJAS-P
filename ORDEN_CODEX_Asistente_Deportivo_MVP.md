# Orden para Codex — Asistente deportivo local, MVP 0.1

Fecha: 29 de octubre de 2026. Documento inicial de producto e implementación.

Este documento completo es la orden de trabajo. Colócalo en `docs/ORDEN_CODEX_MVP.md` de un repositorio nuevo y pide a Codex que lo implemente. No requiere que el usuario tenga instaladas las skills de ChatGPT en su entorno de desarrollo.

## 1. Instrucción principal

Construye en este repositorio una aplicación web local funcional para investigar eventos deportivos y analizar cuotas introducidas manualmente o extraídas de capturas. Debe funcionar de principio a fin: captura o formulario → extracción revisable → identificación del evento → consultas deportivas → cálculos verificables → explicación con fuentes → historial.

Implementa el proyecto, ejecuta las comprobaciones y entrega instrucciones reproducibles. No termines únicamente con un plan ni con una maqueta. Respeta cualquier AGENTS.md aplicable y el contenido existente. Si el repositorio está vacío, crea la estructura propuesta. Resuelve decisiones rutinarias sin pedir confirmaciones; informa de bloqueos reales.

Es un asistente de investigación personal. No implementes colocación de apuestas, conexión a cuentas de casas, depósitos, operaciones de trading ni recuperación de pérdidas. La aplicación debe poder concluir «datos insuficientes» o «sin ventaja demostrada».

## 2. Alcance y prioridades

Competiciones objetivo: Premier League, LaLiga y NBA. La cobertura efectiva depende de las fuentes, temporadas y mercados comprobados.

Primer recorrido completo: fútbol prepartido, resultados 1X2 y totales de goles de partido con líneas de medio gol. Segundo recorrido dentro del MVP: NBA con datos descriptivos de equipos, forma, descanso y evaluación de la cuota; estimaciones propias solo si hay un modelo implementado y evaluado. No simules un predictor NBA para completar una pantalla.

Las capturas pueden contener combinadas. Extrae y presenta todas las selecciones, analiza cada una y señala dependencias; no produzcas una probabilidad conjunta cuando la dependencia no esté modelada.

Fuera de esta versión: análisis predictivo en vivo, props de jugadores, mercados de córners/tarjetas, hándicaps asiáticos con liquidaciones parciales, recomendaciones de importes, cuentas multiusuario y pagos. Reconoce estos mercados en la extracción y muéstralos como no soportados para modelado. Para mercados asiáticos y pushes, nunca reutilices sin ajuste la fórmula binaria.

## 3. Decisión sobre cada repositorio

No hagas un fork de todos ni copies carpetas completas al proyecto. Construye una aplicación propia y encapsula dependencias detrás de adaptadores. Consulta la documentación vigente y verifica APIs, licencias y compatibilidad antes de instalar versiones.

| Proyecto | Decisión inicial | Uso concreto |
| --- | --- | --- |
| https://github.com/machina-sports/sports-skills | Candidato principal para consultas generales. Instalar como dependencia si la versión y sus interfaces superan una prueba mínima. | Calendarios, resultados y consultas deportivas. Reutilizar solo módulos necesarios; no activar trading. |
| https://github.com/martineastwood/penaltyblog | Dependencia para modelo de fútbol, con importación diferida. | Ajustar un modelo Dixon-Coles con datos anteriores al evento y obtener distribución de goles. |
| https://github.com/swar/nba_api | Dependencia especializada NBA. | Registros de partidos y estadísticas de equipos. Aplicar caché y límites de consulta. |
| https://github.com/probberechts/soccerdata | Opcional, no añadir por defecto. | Incorporar un adaptador solo si cubre una carencia concreta de históricos/xG y se verifica la fuente. |
| https://github.com/georgedouzas/sports-betting | Referencia y evaluación posterior. | Estudiar backtesting y diseño de herramientas; evitar añadir otro motor completo en la primera iteración. |
| https://github.com/lacausecrypto/mcp-sports-hub | Referencia arquitectónica. | Inspiración para selección de campos, respuestas pequeñas y catálogo de herramientas. No instalar cientos de herramientas. |
| https://github.com/WFord26/BetTrack | Referencia de producto. | Historial y presentación de cuotas. No arrastrar su stack ni copiar su aplicación. |

Codex puede clonar temporalmente los candidatos fuera del árbol versionado para leer código y ejecutar pruebas de compatibilidad. Registrar revisión consultada y versión utilizada. La aplicación se distribuye con dependencias fijadas y lockfiles; no depende de clones temporales. Si una corrección exige un fork, documentar el motivo y fijar su commit. Copiar utilidades pequeñas solo cuando sea necesario, conservando licencia, atribución y pruebas; preferir la API pública de la biblioteca.

Si sports-skills falla, implementar un adaptador concreto para una fuente verificada en lugar de bloquear toda la aplicación. No afirmar que fuentes gratuitas o scraping garantizan disponibilidad o derechos de redistribución.

Crear `docs/DEPENDENCIES.md`: componente, versión/commit, función comprobada, licencia del código, requisitos y limitaciones de los datos, resultado de smoke test. No instalar paquetes solo por parecerse al nombre del repositorio.

## 4. Stack y ejecución local

- Backend: Python 3.11, FastAPI, Pydantic, SQLAlchemy, SQLite y gestor de dependencias con lockfile. Confirmar requisitos de las bibliotecas elegidas.
- Frontend: React, TypeScript y Vite. Interfaz en español, adaptable a móvil y escritorio.
- Una sola aplicación local, con proceso de trabajos sencillo; no Redis, Kubernetes, microservicios ni base vectorial para este MVP.
- Cola local de tareas y persistencia del estado en SQLite. Marcar trabajos interrumpidos al reiniciar; no dejarlos eternamente en ejecución.
- Fechas almacenadas en UTC y mostradas en America/Lima. Cuotas decimales.
- Proveer arranque de desarrollo y Docker Compose para una ejecución integrada si las dependencias lo permiten. El servicio se vincula a localhost por defecto.

Estructura orientativa:

```text
backend/app/
  api/            # rutas y validación
  schemas/        # ticket, evento, evidencia, informe
  providers/      # adaptadores de fuentes deportivas
  llm/            # extracción, analista, proveedor simulado
  tools/          # catálogo permitido para el analista
  analytics/      # forma, modelo fútbol, cuotas, evaluación histórica
  services/       # trabajos, caché, persistencia y costes
  db/
backend/tests/
frontend/src/
docs/
data/             # ignorado por git salvo fixtures sintéticos
.env.example
README.md
```

## 5. Proveedores de IA

Intención inicial: un modelo OpenAI económico con visión para captura y un modelo DeepSeek con herramientas para coordinar el análisis. OpenAI de mayor capacidad como revisión opcional, desactivada por defecto.

No des por válidos los identificadores, precios ni capacidades mencionados en conversaciones. Comprueba la documentación oficial actual de cada API. Los nombres comerciales de ChatGPT no garantizan que exista un ID equivalente en la API. Si no se puede verificar un ID, deja el campo configurable e informa de ello, sin inventarlo.

Variables de entorno de ejemplo, sin claves reales:

```dotenv
APP_MODE=demo
APP_TIMEZONE=America/Lima
OPENAI_API_KEY=
OPENAI_VISION_MODEL=
OPENAI_REVIEW_MODEL=
DEEPSEEK_API_KEY=
DEEPSEEK_MODEL=
MAX_TOOL_ROUNDS=6
MAX_PARALLEL_TOOLS=3
MAX_OUTPUT_TOKENS=1800
MAX_ANALYSIS_SECONDS=120
MAX_IMAGE_BYTES=10485760
ODDS_PROVIDER=manual
```

Usa SDKs oficiales cuando sean apropiados. Implementa el ciclo real de tool calling: petición → validación de argumentos → ejecución permitida → devolución vinculada al identificador de llamada → siguiente ronda. Una API compatible no garantiza idéntico comportamiento: verifica las exigencias de DeepSeek respecto a razonamiento e historial de herramientas.

No hacen falta credenciales para construir y probar el proyecto: el usuario las configura localmente. Nunca pedir que las pegue en un chat ni guardarlas en git. Los modelos desconocidos o no configurados deben producir errores claros. No cambiar silenciosamente a un modelo más caro.

## 6. Datos y contratos comunes

Cada selección extraída debe contener: deporte, competición si se lee, equipos/jugadores, fecha si aparece, mercado original, mercado normalizado, periodo, línea, lado elegido, cuota, casa si aparece, texto original y campos ambiguos. No inventar el año, fecha, evento o cuota.

El extractor devuelve JSON validado con Pydantic. Imagen ilegible o incompleta → estado `needs_review`. La revisión debe ser editable antes de investigar, incluso cuando la extracción parezca completa.

La identidad de un evento incluye deporte, competición, temporada, inicio UTC e IDs del proveedor. No unir por nombre solamente: distinguir fútbol masculino/femenino, categorías y partidos repetidos. Si hay varias coincidencias, devolver candidatas para elección.

Todas las herramientas devuelven un sobre común:

```json
{
  "status": "ok",
  "event_id": "internal-id",
  "as_of": "ISO-8601 UTC",
  "retrieved_at": "ISO-8601 UTC",
  "source": {"provider": "nombre", "reference": "url o id real"},
  "sample": {"n": 10, "from": "fecha", "to": "fecha"},
  "data": {},
  "warnings": [],
  "missing_fields": [],
  "truncated": false
}
```

Estados: `ok`, `partial`, `unavailable`, `unsupported`, `needs_review`. Adaptar campos no aplicables a null. Diferenciar momento del dato y de descarga; una consulta reciente puede devolver una noticia antigua. Las cifras de ejemplo no son datos reales.

## 7. Herramientas pequeñas para la IA

Implementar una lista permitida, con esquemas estrictos y sin acceso arbitrario a terminal, SQL, archivos o URLs:

1. `resolve_event`: candidatas de evento y sus diferencias.
2. `get_team_form`: ventanas 5/10/20, separación local/visitante, resultados y rivales. Calcular en Python con partidos anteriores al instante de análisis.
3. `get_football_stats`: goles y xG solo donde se verifiquen; conservar muestras y ausencias.
4. `get_nba_stats`: ritmo, eficiencia y registros disponibles; declarar fuente y definición. Descanso calculado con calendario; bajas solo si existe fuente comprobada.
5. `get_match_context`: contexto verificable; inicialmente puede devolver cobertura parcial. No llamar «sin bajas» a una fuente que falló.
6. `predict_football_goals`: modelo ajustado, fecha de corte, distribución, versión y diagnóstico de evaluación.
7. `evaluate_market`: cálculo de probabilidad implícita, margen y EV cuando proceda.

La escritura del historial corresponde al servicio, no al criterio del modelo. Ejecutar en paralelo solo consultas independientes y deduplicar llamadas repetidas. Cargar al modelo únicamente las herramientas pertinentes al deporte.

Reducir tokens mediante campos seleccionados, agregación determinista y paginación. Conservar los datos originales para inspección local según política de retención. No resumir cada respuesta con otra IA: añade coste y puede perder hechos. Un límite de tamaño debe declarar lo omitido y permitir consultar detalles.

MCP es opcional para interoperabilidad futura. Tool calling directo al backend basta para la primera web; no exigir MCP para que funcione DeepSeek.

## 8. Lógica estadística y límites del informe

- Cuota decimal d > 1: probabilidad implícita 1/d.
- Quitar margen proporcional solo con mercado completo de resultados mutuamente excluyentes: q_i / sum(q). Llamarlo referencia de mercado sin margen.
- EV por unidad = p*d−1 solo para mercado binario sin push y con p sustentada. Si p no existe, EV debe ser null.
- Las frecuencias históricas se presentan como conteos, por ejemplo 7/10, sin convertirlas automáticamente en probabilidad futura.
- Modelo de goles: entrenar con información anterior al evento; ponderación temporal configurable y registrada. No añadir lesiones/xG a su fórmula solo porque aparezcan en la explicación.
- Para NBA, el MVP puede describir datos y evaluar precios sin probabilidad propia. Un modelo posterior deberá compararse con un baseline y evaluarse temporalmente.
- Multiplicar probabilidades de una combinada solo en un escenario de independencia explícito. No usar un coeficiente arbitrario de correlación. Selecciones incompatibles deben detectarse.
- No derivar «dinero profesional» únicamente del movimiento de cuota. No clasificar como rentable un modelo por porcentaje de aciertos solamente.
- Separar hechos, resultados del modelo y juicio del analista. La IA no puede alterar probabilidades del motor; cualquier ajuste futuro exige un método documentado.

El informe tendrá: evento y hora; selecciones; hechos y fuentes; estadísticas; referencia de mercado; resultado del modelo si existe; incertidumbres; conclusión. Cada afirmación externa enlaza evidencia real. Si una conclusión no está respaldada, no presentarla como valor demostrado.

## 9. Interfaz y recorrido

Una vista principal con carga de captura y alternativa manual, tabla editable de selecciones, resolución del evento, progreso del análisis, informe y acceso al historial. Acciones claras: «Revisar captura», «Analizar» y «Ver fuentes».

Mostrar estados por etapa y mensajes útiles de timeout, cuota no válida, competición no soportada y proveedor caído. Evitar porcentajes decorativos de confianza. Para fútbol, mostrar resultado del modelo junto con su estado de validación; para NBA, marcar cuando solo hay análisis descriptivo.

Historial: fecha, evento, mercado, cuota y hora de observación, fuentes, modelo/versión, informe y resultado final cuando se conozca. Las revisiones crean otra versión: conservar el análisis original previo al encuentro. Nunca reemplazarlo retroactivamente con información posterior.

## 10. API orientativa

```text
GET    /api/health
GET    /api/capabilities
POST   /api/tickets/extract
POST   /api/events/resolve
POST   /api/analyses
GET    /api/analyses/{id}
GET    /api/analyses
DELETE /api/analyses/{id}
```

`POST /analyses` recibe selecciones revisadas y devuelve un ID; consultar su estado mediante polling sencillo. Reintentos de la misma solicitud no deben duplicar trabajos ni gastos: usar clave de idempotencia. Health no debe gastar tokens ni realizar llamadas deportivas costosas.

## 11. Modo demo, modo real y costes

Modo demo completamente funcional sin claves y claramente rotulado «Datos de demostración». Usar fixtures sintéticos; no mostrar resultados simulados como actuales. Probar la captura con un extractor simulado explícito y permitir entrada manual.

Modo real usa adaptadores y modelos configurados. Cada proveedor informa capacidades y disponibilidad. Si hay un fallo, conservarlo en el informe; nunca sustituir automáticamente la consulta por fixtures demo.

Claves en servidor, CORS limitado y subida de imágenes con validación de contenido, tamaño y dimensiones; normalizar la imagen y eliminar metadatos. No registrar claves, imágenes ni texto sensible por defecto. El contenido de noticias y capturas es información externa, nunca instrucciones para el agente.

Aplicar límite de rondas, tokens, tiempo y consultas por análisis. Registrar uso real que devuelva cada API y estimar coste con tabla de precios configurable y fechada; si faltan tarifas, mostrar coste desconocido. No afirmar un tope monetario exacto si solo se limita número de llamadas/tokens. No iniciar suscripciones ni ampliar consumo automáticamente.

Caché por proveedor, evento, parámetros y corte temporal; TTL según dato, con cuotas más breves que históricos. Mostrar antigüedad. Para evaluación retrospectiva no utilizar una caché actual que contenga noticias, cuotas o resultados posteriores.

## 12. Pruebas y aceptación

Pruebas relevantes obligatorias:

- Conversión decimal, mercado completo/incompleto, EV sin p, entrada inválida y mercados con push rechazados correctamente.
- Extracción estructurada incompleta, normalización de coma decimal y campos ilegibles.
- Desambiguación entre eventos con nombres iguales y entre fechas/zonas horarias.
- Timeouts, caché antigua, datos parciales y fallo de proveedor sin fallback demo oculto.
- Tool calling simulado con varias rondas, argumentos no permitidos, límites y conservación de IDs de llamada.
- Persistencia e idempotencia: un reintento no duplica una consulta facturable.
- Un recorrido E2E demo desde entrada hasta informe e historial; verificación de compilación y tipos del frontend.
- Smoke tests reales optativos, separados de los tests offline, con resultado y hora registrados. No ejecutar consumo de IA sin claves configuradas para pruebas.

Evaluación inicial del modelo fútbol: partición temporal sin mezcla aleatoria y sin información futura. Comparar con un baseline; informar Brier/log loss, tamaño y periodo de la muestra y calibración cuando sea viable. Las cuotas de cierre no pueden alimentar una predicción supuestamente hecha antes. Si faltan datos para evaluar, etiquetar modelo experimental y no mostrar ventaja como validada.

Criterios de aceptación:

1. Se instala y arranca con instrucciones comprobadas.
2. Demo funciona sin claves; modo real muestra configuración pendiente con claridad.
3. Se puede editar lo extraído antes de investigar.
4. Fútbol y NBA tienen adaptadores y estados de cobertura explícitos.
5. Un informe conserva evidencia, fecha de corte, cálculos y limitaciones.
6. Fallos externos no bloquean indefinidamente la interfaz.
7. Historial sobrevive al reinicio y conserva versiones originales.
8. No hay secretos en git, respuestas API o frontend.

## 13. Orden de implementación y entrega

1. Inspeccionar repositorio, verificar dependencias candidatas y registrar decisión. Si una biblioteca no funciona en el entorno, documentar bloqueo concreto y usar interfaces simuladas para continuar las partes independientes.
2. Construir backend, contratos, SQLite, calculadora y demo completa.
3. Construir frontend y recorrido editable de principio a fin.
4. Conectar fuentes reales de fútbol y NBA y comprobar una consulta mínima por proveedor cuando la red lo permita.
5. Integrar extracción OpenAI y analista DeepSeek con pruebas simuladas y límites.
6. Incorporar modelo de goles y evaluación temporal inicial.
7. Ejecutar tests, compilación y comprobación visual disponible; corregir fallos materiales.
8. Entregar README, `.env.example`, lockfiles, `docs/DEPENDENCIES.md`, `docs/ARCHITECTURE.md`, `docs/VALIDATION.md` y `docs/ROADMAP.md`.

En la entrega final de Codex indicar: qué funciona realmente, comandos ejecutados y resultados, qué requiere claves o datos, proveedores probados, limitaciones y siguientes pasos. No llamar terminado al modo real si solo se ejecutó el demo. No publicar ni desplegar externamente como parte de esta orden.

## 14. Referencias iniciales y certeza

La selección de proyectos se basa en documentación pública revisada antes de escribir esta orden, no en una certificación integral de su código ni en pruebas actuales de sus fuentes. Codex debe fijar revisiones y validar compatibilidad durante la implementación.

- Sports Skills: https://github.com/machina-sports/sports-skills
- Modelos de Penaltyblog: https://penaltyblog.readthedocs.io/en/latest/models/overview.html
- Herramientas de agente de sports-betting: https://github.com/georgedouzas/sports-betting/blob/main/docs/interfaces/agents.md
- Configuración de ligas SoccerData: https://github.com/probberechts/soccerdata/blob/master/soccerdata/_config.py
- NBA y limitaciones: https://github.com/swar/nba_api
- Respuestas filtradas MCP Sports Hub: https://github.com/lacausecrypto/mcp-sports-hub
- Cuotas, opción posterior: https://the-odds-api.com/sports-odds-data/sports-apis.html

Las cuotas manuales de capturas bastan para el MVP. Consultar mejores precios entre casas es una ampliación que necesita cobertura efectiva, fecha y reglas de liquidación comparables; no prometerla por tener instalada una biblioteca.
