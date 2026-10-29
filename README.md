# Las Jijas · Asistente deportivo local

Integración local con GitHub `b32a898`: **54 pruebas offline aprobadas**, frontend compilado y valores de `.env` conservados. Se unificaron las correcciones de auditoría con revisión estructurada y límites por etapa. Detalles: [reporte de integración](docs/INTEGRATION_REPORT.md).

MVP 0.1 en español, implementado a partir de [la orden de trabajo](docs/ORDEN_CODEX_MVP.md).
React/TypeScript/Vite + FastAPI/Python 3.11 + SQLAlchemy/SQLite. Investigación personal de fútbol prepartido y NBA descriptiva. No conecta cuentas de apuestas ni ejecuta operaciones.

## Arranque en Windows

Requisitos comprobados: Python 3.11.9, Node 24.12.0, npm 11.6.2. Necesitas red para instalar dependencias; el demo instalado funciona sin claves y sin fuentes externas.

Desde la raíz del repositorio:

```powershell
python -m pip install uv==0.13.6
python -m uv sync --frozen
Copy-Item .env.example .env
cd frontend
npm ci
npm run build
cd ..
.venv/Scripts/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --no-access-log
```

Abre **http://127.0.0.1:8000**. Detén con Ctrl+C. Los informes permanecen en `data/app.db`.
No reemplaces tu `.env` si ya configuraste claves. El servidor también arranca sin ese archivo, en demo por defecto.

Después de instalar `uv`, `./scripts/start.ps1` automatiza instalación fijada, compilación y arranque.

En Linux/macOS sustituye `.venv/Scripts/python` por `.venv/bin/python`. El lockfile incluye las dependencias de plataforma. La ejecución comprobada en esta entrega es Windows; Linux queda pendiente de validación.

## Probar sin claves

1. Pulsa **Cargar fútbol** o **Cargar NBA**.
2. Puedes editar equipos, inicio, mercado, línea, cuota, periodo y hora de observación.
3. Pulsa **Buscar evento** y selecciona la coincidencia con su temporada, categoría y hora.
4. Marca **He revisado equipos, evento, mercado y cuotas** y pulsa **Analizar selecciones**.
5. Revisa cálculo, evaluación temporal, fuentes, ausencias y conclusión. El informe se guarda en **Historial** y se descarga en JSON.
6. **Crear revisión** conserva el original y genera otro trabajo enlazado.

Los eventos demo son ficticios: Lima Azul–Puerto Verde, 1/11/2026 15:00 Lima; Cóndores–Delfines, 1/11/2026 20:00 Lima. Las fechas del demo son fijas para reproducibilidad: el análisis demo usa un corte simulado de 29/10/2026 07:00 Lima, independiente del reloj actual. No se muestran como partidos reales.

**Revisar captura** valida y normaliza la imagen. En demo devuelve un ejemplo simulado explícito, independientemente del contenido: debes revisar y corregir sus campos. En real usa visión OpenAI. Se permiten múltiples selecciones; el backend nunca multiplica probabilidades de una combinada sin dependencia modelada.

## Modo real e IA

Edita `.env` localmente y reinicia:

```dotenv
APP_MODE=real
AI_PROFILE=hybrid
OPENAI_API_KEY=
OPENAI_VISION_MODEL=gpt-6-luna
OPENAI_REVIEW_MODEL=gpt-6.1-sol
DEEPSEEK_API_KEY=
DEEPSEEK_MODEL=deepseek-v4-pro
```

No pongas claves en el frontend o en Git. No se necesitan para consultar calendarios y estadísticas públicas ni para el informe determinista. El perfil `AI_PROFILE=hybrid` usa **GPT-6 Luna** para capturas, **DeepSeek V4 Pro con razonamiento** para el analista con herramientas y **GPT-6.1 Sol** para una revisión final independiente. La revisión no cambia probabilidades, EV ni conclusión del motor. También se conservan `AI_PROFILE=sol` (Sol para visión y análisis mediante Responses) y `AI_PROFILE=economy` (Luna y DeepSeek sin revisión adicional). Consulta [los perfiles](docs/AI_PROFILES.md).

Los valores de `.env.example` son `OPENAI_VISION_MODEL=gpt-6-luna`, `OPENAI_REVIEW_MODEL=gpt-6.1-sol` y `DEEPSEEK_MODEL=deepseek-v4-pro`. Comprueba acceso de tu cuenta; un modelo no disponible produce un estado de indisponibilidad y no se sustituye silenciosamente. La documentación oficial de DeepSeek distingue Pro (`deepseek-v4-pro`) de V4.1 Flash (`deepseek-flash`); no se usa un ID inventado `v4.1-pro`.

OpenAI usa Responses con `store=False`: esfuerzo `low` para visión y `high` para revisión. `OPENAI_REVIEW_MODE=standard` admite `pro` si quieres más trabajo del modelo, latencia y consumo. `OPENAI_REVIEW_ENABLED=false` desactiva esa revisión. DeepSeek usa Chat Completions con `DEEPSEEK_THINKING=true` y `DEEPSEEK_REASONING_EFFORT=high` (también low/max). Se conserva su `reasoning_content` entre rondas en memoria; no se persiste. Las claves permanecen en el servidor.

Referencias: [GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna), [GPT-6.1 Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol), [modo Pro OpenAI](https://developers.openai.com/api/docs/guides/reasoning#reasoning-mode), [modelos DeepSeek](https://api-docs.deepseek.com/), [razonamiento y herramientas](https://api-docs.deepseek.com/guides/thinking_mode/).

Para comprobar acceso sin generar respuestas, desde la raíz:

```powershell
$env:PYTHONPATH='backend'
.venv/Scripts/python scripts/check_ai.py
```

`scripts/check_ai.py --smoke` hace llamadas **facturables** con datos sintéticos, bajo los límites de `.env`, y registra uso en la base separada `data/ai-smoke.db`. Es optativo: la instalación y los tests no lo ejecutan. La integración tiene pruebas de solicitudes y respuestas simuladas; **no se ha validado una llamada IA real en esta actualización porque faltan claves**. Que un modelo figure en la lista no garantiza cuota disponible ni éxito de una llamada posterior.

Consulta `/api/capabilities` para configuración pendiente. La disponibilidad real puede variar por red, temporada y proveedor. No hay sustitución de errores reales por fixtures demo.

## Datos y modelo

- Calendarios: ESPN, separados por Premier League masculina, LaLiga masculina y NBA. Debes confirmar la identidad; no se resuelve por nombre solamente.
- Fútbol histórico: `sports-skills` detrás de adaptador. Solo se admite la fuente explícita ESPN con IDs válidos. Se deduplica por competición/evento; duplicados contradictorios invalidan la consulta. El modelo utiliza IDs ESPN estables, con nombres solo como etiquetas. Sin identidad/muestra suficiente, queda no disponible.
- NBA: `nba_api` con logs de temporada, registros, últimos partidos y descanso aproximado. Ritmo, eficiencias, bajas y predictor propios no están disponibles; aparecen como ausencias explícitas.
- Fútbol: Dixon-Coles de `penaltyblog`, importación diferida, ponderación exponencial `MODEL_XI`, corte anterior al evento, mínimo 60 partidos y 5 apariciones por equipo. Distribución normalizada de goles; mercados 1X2 y totales de partido de 0,5 a 9,5, solo medios goles. Se calcula la línea solicitada.
- Evaluación actual: 80% inicial y bloques cronológicos con entrenamiento creciente sobre todo el bloque posterior, sin separar timestamps simultáneos. Brier multiclase, log loss, baseline suavizado por entrenamiento, calibración de las tres clases y evaluación binaria por línea de total. Se registran IDs, omisiones y hash de entrada. Los intervalos normales son descriptivos, no corrigen toda la dependencia entre partidos. Siempre **experimental**. `docs/MODEL_EVALUATION.json` conserva la evaluación histórica del protocolo anterior; no representa una nueva evaluación de esta versión.
- El EV experimental es un resultado del modelo sin validación económica. La conclusión no presenta ventaja demostrada. Las frecuencias históricas son conteos, no probabilidades futuras.
- Solo se elimina margen proporcional con todas las cuotas del mercado mutuamente excluyente. Líneas enteras, cuartos, props, vivo y otros periodos no reciben EV binario.
- La cuota del lado seleccionado debe coincidir con el mercado completo para quitar margen. Cambiar evento, mercado, línea o precio invalida las cuotas completas del formulario.
- En real se rechazan cuotas observadas después del corte o del inicio. Se suspende el EV para precios de más de `MAX_QUOTE_AGE_HOURS` (24) y la probabilidad aplicable/EV para históricos de más de `MAX_HISTORY_AGE_DAYS` (30). No se reemplazan por datos sintéticos.

Fechas UTC, interfaz America/Lima. Las fechas de resultados usadas para el corte son conservadoras: fútbol inicio +6 h; NBA, fecha de calendario +1 día a las 12:00 UTC. No son sellos oficiales de actualización. No hay evaluación retrospectiva de eventos ya iniciados usando datos actuales.

## Desarrollo y comprobaciones

Dos terminales desde la raíz:

```powershell
.venv/Scripts/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload --no-access-log
```

```powershell
cd frontend
npm run dev
```

Frontend: http://127.0.0.1:5173, proxy `/api` al backend.

```powershell
.venv/Scripts/python -m pytest -q
cd frontend
npm run build
```

Los tests offline usan una base temporal y no llaman a IA ni a proveedores deportivos. Smoke de consultas públicas, optativo y separado:

```powershell
$env:PYTHONPATH='backend'
.venv/Scripts/python scripts/smoke_providers.py
```

Escribe `docs/LIVE_SMOKE.json` y una caché separada `data/smoke.db`. No prueba claves ni habilita gasto de IA. Véase [VALIDATION](docs/VALIDATION.md).

## Docker Compose

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Abre http://127.0.0.1:8000. Un volumen mantiene SQLite. El puerto del host se limita a localhost; el contenedor escucha internamente en 0.0.0.0. **Docker no estaba instalado en el entorno de entrega: configuración proporcionada, construcción y arranque Docker no comprobados.**

## API y operación

FastAPI documenta contratos en `/docs`. Rutas: health, capabilities, tickets/extract, events/resolve, analyses (crear/listar/consultar/eliminar). Crear análisis exige selecciones revisadas y cabecera `Idempotency-Key`; repetir la misma solicitud devuelve el mismo trabajo sin gastos adicionales. Cambiar el contenido con la misma clave devuelve 409. Un fallo no se reintenta con cargos automáticamente.

Ejecuta **un solo proceso** de servidor y un worker local. La cola tiene capacidad 25; su estado se conserva en SQLite. Al reiniciar, trabajos queued/running pasan a interrupted; crea una revisión para continuar. `--workers` con varios procesos no está soportado en esta versión.

Límites: 20 selecciones, 6 rondas IA, 12 llamadas de herramienta por ronda y 3 paralelas. Presupuestos por respuesta: visión 4.096 tokens, analista 8.192 y revisión 8.192, incluidos tokens de razonamiento. Plazo global 240 s, cálculo 45 s y cada etapa IA hasta 90 s, ajustado al plazo restante. Configuración en `.env.example`. Consultas SDK y ajuste estadístico se aíslan en procesos terminables; selecciones del mismo evento/corte comparten ajuste. Una consulta SDK puede realizar varios HTTP internos.

Las imágenes se limitan por bytes, formato y dimensiones, se normalizan a JPEG sin metadatos y no se persisten. Se guardan localmente las selecciones revisadas, informes, caché y uso API. Los datos originales de temporada permanecen en caché para inspección local. TTL: calendario 5 min, NBA 1 h, fútbol 6 h. El sello de descarga original se conserva en caché; cada fila histórica mantiene su procedencia cuando está disponible. La retención local actual es indefinida hasta borrado manual; no hay limpieza programada. El borrado de un análisis no elimina caché ni registro de uso API.

El uso devuelto por cada API se registra en SQLite inmediatamente, incluso si falla una ronda posterior. La estimación del informe solo se calcula cuando el uso corresponde exclusivamente al analista activo y hay `INPUT_PRICE`, `OUTPUT_PRICE`, `PRICE_DATE` y `PRICE_MODEL` coincidente con su ID. Si interviene la revisión OpenAI, queda desconocido hasta implementar precios por modelo. La extracción mantiene su uso separado; no se calcula factura total. No se deducen precios comerciales ni se promete un tope monetario exacto.

Documentación: [dependencias](docs/DEPENDENCIES.md), [arquitectura](docs/ARCHITECTURE.md), [validación](docs/VALIDATION.md), [pendientes](docs/ROADMAP.md).
