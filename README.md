# Las Jijas · Asistente deportivo local

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
OPENAI_API_KEY=
OPENAI_VISION_MODEL=
DEEPSEEK_API_KEY=
DEEPSEEK_MODEL=
```

No pongas claves en el frontend o en Git. No se necesitan para consultar calendarios y estadísticas públicas ni para el informe determinista. Sí son necesarias para leer una captura con IA y para el comentario de DeepSeek. La revisión OpenAI de mayor capacidad está desactivada y no se invoca.

Los modelos se dejan vacíos deliberadamente: elige un ID habilitado para tu cuenta y comprueba sus capacidades en [OpenAI Docs](https://developers.openai.com/api/docs/guides/images-vision) y la [documentación DeepSeek](https://api-docs.deepseek.com/guides/thinking_mode/). Un ID desconocido causa un error de proveedor; no se cambia automáticamente por otro. Las integraciones están implementadas y el ciclo de herramientas tiene pruebas simuladas; **no se hicieron llamadas de IA facturables**.

Consulta `/api/capabilities` para configuración pendiente. La disponibilidad real puede variar por red, temporada y proveedor. No hay sustitución de errores reales por fixtures demo.

## Datos y modelo

- Calendarios: ESPN, separados por Premier League masculina, LaLiga masculina y NBA. Debes confirmar la identidad; no se resuelve por nombre solamente.
- Fútbol histórico: `sports-skills` detrás de adaptador, API pública de temporadas y resumen. El paquete puede usar ESPN u openfootball; el adaptador solo admite históricos con identidad ESPN y descarta el fallback openfootball sin una equivalencia de IDs comprobada. Las identidades de equipos se relacionan mediante IDs del proveedor cuando existen. Sin identidad/muestra suficiente, el modelo queda no disponible.
- NBA: `nba_api` con logs de temporada, registros, últimos partidos y descanso aproximado. Ritmo, eficiencias, bajas y predictor propios no están disponibles; aparecen como ausencias explícitas.
- Fútbol: Dixon-Coles de `penaltyblog`, importación diferida, ponderación exponencial `MODEL_XI`, corte anterior al evento, mínimo 60 partidos y 5 apariciones por equipo. Distribución normalizada de goles; mercados 1X2 y total de partido con medio gol.
- Evaluación inicial: división temporal 80/20, hasta 30 partidos de validación, baseline de frecuencias 1X2 del entrenamiento con suavizado. Brier multiclase (suma de tres errores), log loss y calibración por intervalos. Siempre **experimental**, incluso si supera el baseline en la muestra inicial.
- El EV experimental es un resultado del modelo sin validación económica. La conclusión no presenta ventaja demostrada. Las frecuencias históricas son conteos, no probabilidades futuras.
- Solo se elimina margen proporcional con todas las cuotas del mercado mutuamente excluyente. Líneas enteras, cuartos, props, vivo y otros periodos no reciben EV binario.

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

Límites: 20 selecciones, 6 rondas IA, 12 llamadas de herramienta por ronda, 3 paralelas, 1.800 tokens de salida por respuesta y 120 segundos por análisis, configurables donde indica `.env.example`. Las consultas SDK síncronas se aíslan en procesos terminables para evitar consultas que sobrevivan indefinidamente al timeout. Una consulta del SDK puede realizar varios HTTP internos.

Las imágenes se limitan por bytes, formato y dimensiones, se normalizan a JPEG sin metadatos y no se persisten. Se guardan localmente las selecciones revisadas, informes, caché y uso API. Los datos originales de temporada permanecen en caché para inspección local. TTL: calendario 5 min, NBA 1 h, fútbol 6 h. El sello de descarga original se conserva en caché; cada fila histórica mantiene su procedencia cuando está disponible. La retención local actual es indefinida hasta borrado manual; no hay limpieza programada. El borrado de un análisis no elimina caché ni registro de uso API.

El uso devuelto por cada API se registra en SQLite inmediatamente, incluso si falla una ronda posterior. La estimación de coste del informe solo cubre el analista DeepSeek y requiere `INPUT_PRICE`, `OUTPUT_PRICE` (USD por millón) y `PRICE_DATE`. La extracción muestra uso/coste desconocido por separado; no se calcula factura total. No se deducen precios comerciales ni se promete un tope monetario exacto.

Documentación: [dependencias](docs/DEPENDENCIES.md), [arquitectura](docs/ARCHITECTURE.md), [validación](docs/VALIDATION.md), [pendientes](docs/ROADMAP.md).
