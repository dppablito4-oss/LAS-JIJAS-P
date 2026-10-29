# Dependencias y fuentes revisadas

Revisión: 29/10/2026. Python 3.11.9 / Windows. `uv.lock` fija las 104 dependencias instaladas y hashes; `frontend/package-lock.json` fija frontend y transitivas. No se copiaron aplicaciones ni utilidades de terceros. Se usan APIs públicas detrás de adaptadores.

## Candidatos de la orden

**sports-skills 0.40.0 — MIT.** Dependencia instalada desde PyPI después de contrastar el `pyproject.toml` del repositorio (nombre, versión, Python >=3.9.10 e interfaces). Revisión consultada: `ee30e2539f2f6d6d036cf97c39efbc6e8efb8ac1`. [Repositorio](https://github.com/machina-sports/sports-skills/tree/ee30e2539f2f6d6d036cf97c39efbc6e8efb8ac1). Se verificaron firmas de `football.get_daily_schedule`, `get_season_schedule`, `get_team_schedule`, `get_event_summary`. Smoke real `get_season_schedule(season_id='premier-league-2025')`: 380 partidos. También respondió calendario diario del 29/10/2026. Producción usa temporadas/resumen; resolución inicial de evento usa ESPN directo para reducir consultas a ligas específicas. Sin módulos de mercados, wallets ni trading. Datos sujetos a términos de ESPN/openfootball; MIT cubre el código, no concede derechos generales sobre datos. El SDK tiene fallback interno a openfootball: el adaptador descarta los resultados openfootball si no hay equivalencia de IDs ESPN verificada, sin fallback a fixtures demo. Cada temporada puede implicar varias solicitudes internas; corre en proceso con timeout terminable.

**penaltyblog 1.13.1 — MIT verificada en el archivo `licenses/LICENCE` del wheel instalado.** Python >=3.10, wheel Windows/Python 3.11 instalado y smoke de ajuste Dixon-Coles ejecutado. Revisión consultada: `6870f0e762e9cba35fa722dc14a8daeaf8bc6134`. [Repositorio](https://github.com/martineastwood/penaltyblog/tree/6870f0e762e9cba35fa722dc14a8daeaf8bc6134), [modelos](https://penaltyblog.readthedocs.io/en/latest/models/overview.html). API comprobada: constructor, `fit`, `predict`, `home_draw_away`, `total_goals('over', line)`, `grid`. Importación diferida. Distribución normalizada y evaluación temporal probadas offline; no se usan scrapers, importes ni cuotas de cierre del paquete. Licencias/derechos de los datos son independientes. Dependencia relativamente grande con transitivas científicas; Linux/Docker no comprobados.

**nba_api 1.12.0 — MIT.** Python >=3.10, importación y consulta real `LeagueGameLog(season='2025-26', timeout=10)` comprobadas: 2.460 filas de equipos (dos por partido, no 2.460 partidos). Revisión consultada: `83444e14dd3c8848a197a677be06b7ed2e869ae9`. [Repositorio](https://github.com/swar/nba_api/tree/83444e14dd3c8848a197a677be06b7ed2e869ae9), [endpoint](https://github.com/swar/nba_api/blob/master/docs/nba_api/stats/endpoints/leaguegamelog.md). Datos NBA sujetos a condiciones y bloqueos geográficos o de red; no SLA. Solo temporada regular en el adaptador inicial. No predictor NBA ni datos verificados de bajas/ritmo/eficiencias.

**soccerdata: no instalado**, conforme a la orden. No hay carencia demostrada que justifique otro scraper.

**sports-betting, mcp-sports-hub y BetTrack: no instalados ni copiados.** La orden los sitúa como referencias y evaluación posterior. No se verificó su ejecución ni se les atribuye cobertura del producto.

**Football-Data: descarga descartada.** Su [página de datos](https://football-data.co.uk/data.php), revisada el 29/10/2026, restringe uso automatizado para productos de datos/entrenamiento con IA. No existe adaptador de descarga de esa fuente en el código final. La presencia de una biblioteca con scraper no elimina las restricciones de la fuente.

## Runtime de la aplicación

- FastAPI 0.162.0: MIT; arranque y API probados.
- Uvicorn 0.54.0: BSD-3-Clause; arranque HTTP localhost comprobado.
- SQLAlchemy 2.1.6: MIT; SQLite, unicidad de idempotencia, recuperación y persistencia probados.
- Pydantic 2.14.2 y pydantic-settings 2.16.2: MIT; JSON estricto y configuración .env.
- Pillow 12.3.0: MIT-CMU; formatos, dimensiones, límite de bytes y eliminación de metadatos comprobados.
- httpx 0.28.1: BSD-3-Clause; ESPN público y timeouts.
- OpenAI SDK 3.41.0: Apache-2.0; interfaces Responses y Chat Completions verificadas en documentación vigente e importación local. DeepSeek documenta el uso del SDK OpenAI compatible. No hay SDK oficial DeepSeek separado instalado. Integración probada mediante respuestas simuladas; no se hicieron llamadas facturables.
- React/React DOM 19.2.0: MIT. TypeScript 5.9.3: Apache-2.0. Vite 7.3.7: MIT. Instalación npm y compilación comprobadas con Node 24.12.0.
- uv 0.13.6: gestor de entorno y lockfile. `uv sync --frozen` comprobado. Sin dependencia de clones temporales.

## Documentación IA consultada

- [OpenAI Docs: visión con Responses](https://developers.openai.com/api/docs/guides/images-vision): input_image, data URL y modelo con capacidad de visión. IDs configurables, sin asumir que un nombre de ChatGPT equivale a una API.
- [DeepSeek: thinking y herramientas](https://api-docs.deepseek.com/guides/thinking_mode/): se conserva `reasoning_content` en el historial en memoria de todas las rondas con herramientas; los resultados vuelven con `tool_call_id`. El razonamiento no se guarda en informes ni logs. No se fijan precios ni un ID de modelo sin selección del operador.

Resultados con hora UTC: [LIVE_SMOKE.json](LIVE_SMOKE.json). Una respuesta válida hoy no garantiza disponibilidad futura ni derechos de redistribución.
