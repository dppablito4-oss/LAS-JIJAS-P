import asyncio
import hashlib
import json
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from .schemas import Selection, AnalysisRequest, now
from .config import settings
from .db import init, Session, Job, serial
from .providers import resolve, unavailable
from .llm import extract
from .service import run_job

queue=asyncio.Queue(maxsize=25)


async def worker():
    while True:
        jid=await queue.get()
        try: await run_job(jid)
        finally: queue.task_done()


@asynccontextmanager
async def lifespan(app):
    global queue
    queue=asyncio.Queue(maxsize=25)
    init()
    task=asyncio.create_task(worker())
    yield
    task.cancel()
    try: await task
    except asyncio.CancelledError: pass


app=FastAPI(title='Las Jijas · Asistente deportivo',lifespan=lifespan)
app.add_middleware(TrustedHostMiddleware,allowed_hosts=['localhost','127.0.0.1','testserver'])
app.add_middleware(CORSMiddleware,allow_origins=['http://localhost:5173','http://127.0.0.1:5173'],allow_methods=['GET','POST','DELETE'],allow_headers=['Content-Type','Idempotency-Key'])


@app.middleware('http')
async def local_origin(request,call_next):
    origin=request.headers.get('origin')
    if origin and origin not in ['http://localhost:5173','http://127.0.0.1:5173','http://localhost:8000','http://127.0.0.1:8000']:
        return JSONResponse({'detail':'Origen no permitido.'},status_code=403)
    return await call_next(request)


@app.get('/api/health')
def health(): return {'status':'ok','mode':settings.app_mode}


@app.get('/api/capabilities')
def capabilities():
    return {'mode':settings.app_mode,'timezone':settings.app_timezone,'competitions':['Premier League','LaLiga','NBA'],
        'football':'1X2 y totales con medio gol. Dixon-Coles experimental; requiere históricos con identidad verificada.',
        'nba':'Solo descriptivo. Ritmo, eficiencias y lesiones pendientes de cobertura.',
        'vision_configured':bool(settings.openai_api_key and settings.vision_model),
        'analyst_configured':settings.analyst_configured,
        'ai':settings.ai_summary(),
        'review_enabled':False,'cost':'Desconocido sin tarifas configuradas y fechadas.',
        'providers':['demo-synthetic'] if settings.app_mode=='demo' else ['ESPN','sports-skills','nba_api']}


@app.get('/api/demo-ticket')
def demo_ticket(sport:str='football'):
    if settings.app_mode!='demo': raise HTTPException(404,'Solo disponible en modo demo.')
    from .providers import demo_events
    e=next((e for e in demo_events() if e.sport==sport),None)
    if not e: raise HTTPException(422,'Deporte no soportado.')
    return Selection(sport=e.sport,competition=e.competition,home=e.home,away=e.away,starts_at=e.starts_at,
                     market='1x2' if sport=='football' else 'moneyline',side='home',odds=2.1)


@app.post('/api/tickets/extract')
async def extract_ticket(file: UploadFile=File()):
    raw=await file.read(settings.max_image_bytes+1)
    try: return await asyncio.wait_for(extract(raw),40)
    except ValueError as e: raise HTTPException(422,str(e))
    except Exception: raise HTTPException(502,'Extractor no disponible, modelo inválido o timeout. Revisa configuración; puedes introducir los datos manualmente.')


@app.post('/api/events/resolve')
async def resolve_event(selection:Selection):
    try: return await asyncio.wait_for(resolve(selection),40)
    except Exception: return unavailable('sports','Calendario no disponible o timeout; no se usaron fixtures demo.')


@app.post('/api/analyses',status_code=202)
async def create_analysis(request:AnalysisRequest,idempotency_key:str=Header(min_length=8,max_length=150)):
    if any(not s.odds or not s.home or not s.away or s.ambiguous_fields for s in request.selections):
        raise HTTPException(422,'Completa equipos, cuota y resuelve los campos ambiguos antes de analizar.')
    body=request.model_dump_json()
    canonical=json.dumps(request.model_dump(mode='json',exclude_unset=True),sort_keys=True)
    digest=hashlib.sha256(canonical.encode()).hexdigest()
    with Session() as db:
        existing=db.scalar(select(Job).where(Job.key==idempotency_key))
        if existing:
            if existing.digest!=digest: raise HTTPException(409,'La clave de idempotencia ya se usó con otros datos.')
            return serial(existing)
        if request.parent_id and not db.get(Job,request.parent_id): raise HTTPException(404,'Análisis original no encontrado.')
        if queue.full(): raise HTTPException(429,'Cola llena. Espera un momento.')
        job=Job(id=str(uuid.uuid4()),key=idempotency_key,digest=digest,created_at=now().isoformat(),status='queued',request=body)
        db.add(job)
        try: db.commit()
        except IntegrityError:
            db.rollback();existing=db.scalar(select(Job).where(Job.key==idempotency_key))
            if not existing or existing.digest!=digest: raise HTTPException(409,'Conflicto de idempotencia.')
            return serial(existing)
        queue.put_nowait(job.id)
        return serial(job)


@app.get('/api/analyses')
def list_analyses(limit:int=50,offset:int=0):
    with Session() as db:
        return [serial(j) for j in db.scalars(select(Job).order_by(Job.created_at.desc()).limit(max(1,min(limit,100))).offset(max(0,offset)))]


@app.get('/api/analyses/{jid}')
def get_analysis(jid:str):
    with Session() as db:
        job=db.get(Job,jid)
        if not job: raise HTTPException(404,'Análisis no encontrado.')
        return serial(job)


@app.delete('/api/analyses/{jid}')
def delete_analysis(jid:str):
    with Session.begin() as db:
        job=db.get(Job,jid)
        if not job: raise HTTPException(404,'Análisis no encontrado.')
        if job.status in ['queued','running']: raise HTTPException(409,'Espera a que termine el trabajo.')
        db.delete(job)
    return {'deleted':True}


if Path('frontend/dist').exists():
    app.mount('/',StaticFiles(directory='frontend/dist',html=True),name='frontend')
