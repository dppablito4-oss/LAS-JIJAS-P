# Reporte de implementación y validación

Este documento conserva la validación de la entrega original. Para las correcciones e integración IA posteriores del mismo día, consulta [la actualización](IMPLEMENTATION_UPDATE_2026-10-29.md). Sus métricas y límites no deben atribuirse automáticamente a la versión actual.

Fecha: **29 de octubre de 2026**, America/Lima. Entorno Windows, Python 3.11.9, Node 24.12.0 y npm 11.6.2. Código local, sin publicación ni despliegue externo.

## Lo que funciona y se comprobó

- Backend FastAPI arranca en localhost y sirve la compilación React. GET `/` y `/api/health` respondieron HTTP 200.
- Entrada manual y captura simulada, contratos estrictos, revisión editable, resolución explícita del evento, cola local, cálculo, informe, exportación JSON e historial persistente con revisiones.
- Demo fútbol y NBA sin claves. Fútbol ajusta Dixon-Coles y calcula 1X2/totales de medio gol. NBA devuelve descripciones/registros; no simula probabilidades futuras.
- Idempotencia con índice único en SQLite; contenido distinto con clave reutilizada devuelve 409. Al reiniciar, queued/running pasan a interrupted. El informe completado sobrevive a la reapertura de la aplicación.
- Tool calling simulado con varias rondas, IDs originales, conservación de `reasoning_content` en memoria, argumentos estrictos, herramientas no permitidas, deduplicación y límite de rondas.
- Mercados completos/incompletos, coma decimal, entrada inválida, EV sin probabilidad, rechazo de pushes/cuartos y periodos fuera de alcance, incompatibilidades, fechas/zonas, corte temporal, caché expirada, fallo de proveedor sin demo oculto y normalización de imágenes.

## Comandos ejecutados

```powershell
python -m pip install uv
python -m uv sync
python -m uv sync --frozen
.venv/Scripts/python -m pytest -q
cd frontend
npm install
npm run build
npm audit --omit=dev
```

Resultado: instalación de 104 paquetes Python fijados, sincronización frozen correcta, **25 tests offline aprobados**, compilación TypeScript/Vite correcta y auditoría npm de dependencias de producción con **0 vulnerabilidades reportadas**. La auditoría no constituye un análisis integral de seguridad ni cubre las dependencias Python.

Se corrigieron dos problemas detectados al ejecutar pruebas: BOM de PowerShell en `pyproject.toml` y cola asyncio ligada al loop de un ciclo anterior del servidor. La base temporal de pruebas se cierra antes de limpiarla en Windows. Se corrigieron caracteres dañados en dos textos insertados por terminal.

## Fuentes reales

Ejecutado sin credenciales ni IA:

```powershell
$env:PYTHONPATH='backend'
.venv/Scripts/python scripts/smoke_providers.py
.venv/Scripts/python scripts/evaluate_football.py
```

[LIVE_SMOKE.json](LIVE_SMOKE.json) conserva fecha UTC, estado y conteos. Consulta iniciada a las **12:56:53 de Lima**:

- sports-skills 0.40.0, `get_season_schedule('premier-league-2025')`: **380 partidos**, fuente reportada ESPN.
- nba_api 1.12.0, `LeagueGameLog('2025-26')`: **2.460 registros de equipos**, correspondientes a dos registros por encuentro.
- ESPN Premier League: **10 candidatos** en la ventana de tres días consultada.
- ESPN LaLiga: **9 candidatos**.
- ESPN NBA: **26 candidatos**.

Los calendarios se marcan `partial`: una respuesta HTTP válida no prueba cobertura completa. Son pruebas puntuales; no garantizan disponibilidad futura. No se probaron todos los equipos, temporadas o endpoints.

## Evaluación inicial del modelo con datos reales

[MODEL_EVALUATION.json](MODEL_EVALUATION.json) registra el resultado íntegro excepto la matriz de marcadores. Consulta iniciada a las **13:01:13 de Lima**. Se resolvió un evento real de Premier League y se entrenó con **380 partidos** disponibles de 2025–26. No se obtuvo histórico utilizable de la temporada 2026 durante ese recorrido: la última observación es **24/05/2026**. La aplicación advierte cuando los históricos tienen más de 30 días.

Validación temporal: 304 partidos de entrenamiento, terminados antes del bloque de evaluación; se evaluaron los últimos 30 partidos del bloque posterior, del 9 al 24 de mayo de 2026. No se mezcló aleatoriamente ni se usaron cuotas de cierre.

- Brier multiclase: **0,5841**, baseline **0,6587**.
- Log loss: **0,9816**, baseline **1,0889**.
- Calibración por cinco intervalos disponible en el JSON; tamaños de 1 a 13 observaciones por intervalo, insuficientes para una conclusión estable.

Aunque estas métricas superan el baseline en esa muestra, **el modelo sigue experimental y no demuestra rentabilidad ni ventaja actual**. Hay selección limitada de periodo, muestra pequeña y datos antiguos respecto al evento resuelto. El EV del motor se etiqueta orientativo; la conclusión sigue «Sin ventaja demostrada». No se evalúa un predictor NBA inexistente.

## Comprobación de interfaz

La página compilada se abrió en Comet en una pestaña nueva, http://127.0.0.1:8000. Se inspeccionó el árbol accesible: título, rótulo demo, entrada de captura/manual, ejemplos fútbol/NBA, campos editables, fechas Lima, búsqueda, confirmación de revisión, botón Analizar e historial estaban presentes. El servidor respondió correctamente.

La conexión de automatización de navegador no estaba disponible. El fallback a ventana nativa permitió leer el árbol, pero la captura falló con `window capture timed out` / `FrameArrived timed out`, y los clics con `coordinate input geometry is unavailable`. Por ello **no se afirma una revisión visual por screenshot ni E2E de clics**. El E2E automatizado comprobado es de API, desde subida de imagen hasta informe/historial y reinicio. El CSS tiene reglas móviles; viewport móvil no verificado visualmente.

## Qué requiere configuración o trabajo posterior

- IA real: claves y modelos locales de OpenAI/DeepSeek. Se verificaron documentación e interfaces, con tests simulados; **no se ejecutó una llamada IA facturable** ni se comprobó la calidad de visión sobre capturas reales.
- Docker: archivos presentes; el comando `docker --version` indicó que Docker no está instalado. No se construyó ni ejecutó la imagen. El arranque nativo sí se probó.
- Ritmo/eficiencia NBA, xG, bajas y alineaciones no tienen cobertura verificada en este MVP. Se declaran como ausencias.
- El resultado final se conserva como null hasta implementar una fuente o registro separado; no existe liquidación/actualización automática de resultados.
- Coste consolidado, limpieza automática, paginación visible del historial y revisión visual móvil quedan en [ROADMAP](ROADMAP.md).

La demo y las consultas deportivas reales están comprobadas. **La integración real completa con IA no se declara validada**. No se configuraron claves, suscripciones, cuentas de casas ni operaciones financieras.
