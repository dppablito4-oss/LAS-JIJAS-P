import asyncio
import json
from datetime import datetime
from .schemas import AnalysisRequest, Event, now
from .config import settings
from .db import Session, Job
from . import providers
from .analytics import evaluate, dependencies
from .tools import ToolBox
from .llm import analyze


async def build_report(request,scope='analysis'):
    cutoff='2026-10-29T12:00:00+00:00' if settings.app_mode=='demo' else now().isoformat()
    contexts=[];results=[];usage=[]
    for s in request.selections:
        c={'selection':s,'warnings':[]}
        try:
            evidence=await asyncio.wait_for(providers.resolve(s),40)
            c['resolution']=evidence.model_dump(mode='json')
            candidates=[Event.model_validate(e) for e in evidence.data.get('candidates',[])]
            event=next((e for e in candidates if e.id==s.event_id),None) if s.event_id else None
            if not event:
                c['warnings'].append('Elige y confirma un evento candidato antes de analizar.')
            elif event.starts_at<=datetime.fromisoformat(cutoff):
                c['warnings'].append('Evento iniciado o pasado: modelado prepartido no disponible. No se reconstruye una predicción histórica con datos actuales.')
            else:
                c['event']=event;c['provider']='demo-synthetic' if settings.app_mode=='demo' else 'sports-skills / ESPN' if s.sport=='football' else 'NBA Stats'
                try:
                    rows,reference=await providers.histories(event,cutoff)
                    c['rows']=rows;c['reference']=reference
                    c['data_as_of']=datetime.fromisoformat(max((r['date'] for r in rows),default=cutoff))
                    dates=[datetime.fromisoformat(r['retrieved_at']) for r in rows if r.get('retrieved_at')]
                    if dates: c['data_retrieved_at']=min(dates)
                    if rows and (datetime.fromisoformat(cutoff)-c['data_as_of']).days>30:
                        c['warnings'].append('Históricos con más de 30 días de antigüedad; cobertura reciente incompleta.')
                except Exception:
                    c['warnings'].append('Fuente histórica no disponible o timeout. No se utilizaron datos demo.')
                if s.sport=='football' and c.get('rows'):
                    from .model import predict
                    try:
                        c['model']=await asyncio.wait_for(asyncio.to_thread(predict,c['rows'],event.home,event.away,cutoff),25)
                    except Exception:
                        c['model']={'status':'unavailable','reason':'El ajuste no se completó o superó el límite de tiempo.'}
                if s.sport=='football' and settings.app_mode=='real':
                    # Only the public read-only summary module is called; no trading modules.
                    from .isolated import query
                    try:
                        raw=await query('football-context',event.id.split(':')[-1],12)
                        c['context']={'provider_status':raw.get('status'),'reference':event.reference,
                                      'note':'Consulta sports-skills realizada; no se infieren bajas de esta respuesta.'}
                    except Exception:
                        c['context']={'status':'unavailable'}
        except Exception:
            c['resolution']=providers.unavailable('sports','No se pudo consultar el calendario; revisa la configuración o reintenta.').model_dump(mode='json')
        model=c.get('model',{});p=None
        if model.get('status')=='experimental':
            if s.market=='1x2' and s.side in ['home','draw','away']: p=model['home_draw_away'][['home','draw','away'].index(s.side)]
            if s.market=='total' and str(s.line) in model.get('totals',{}) and s.side in ['over','under']:
                over=model['totals'][str(s.line)];p=over if s.side=='over' else 1-over
        c['market']=evaluate(s,p);contexts.append(c)
    box=ToolBox(contexts,cutoff)
    for i,c in enumerate(contexts):
        s=c['selection'];ev=c.get('event')
        toolnames=['get_team_form','get_match_context','get_football_stats' if s.sport=='football' else 'get_nba_stats']
        evidence=[await box.call(n,{'selection_index':i}) for n in toolnames]
        results.append({'selection':s.model_dump(mode='json'),'event':ev.model_dump(mode='json') if ev else None,
            'resolution':c['resolution'],'market':c['market'],'model':c.get('model'),
            'evidence':evidence,'warnings':c['warnings'],
            'conclusion':'Datos insuficientes' if not ev or not c.get('rows') else 'Sin ventaja demostrada',
            'model_note':'Modelo experimental; EV orientativo, sin ventaja validada.' if c.get('model',{}).get('status')=='experimental' else 'Sin probabilidad propia sustentada. NBA: análisis descriptivo.' if s.sport=='nba' else 'Modelo no disponible.'})
    analyst='Demo: explicación determinista; no se consultó IA.'
    if settings.app_mode=='real':
        try: analyst=await asyncio.wait_for(analyze(box,usage,scope),40)
        except Exception: analyst='Analista no disponible o timeout. Se conserva evidencia y uso de rondas completadas.'
    cost=None
    if not usage: cost=0 if settings.app_mode=='demo' else None
    elif settings.input_price is not None and settings.output_price is not None and settings.price_date and settings.price_model==settings.analyst_model:
        cost=sum(u.get('prompt_tokens',u.get('input_tokens',0))*settings.input_price+u.get('completion_tokens',u.get('output_tokens',0))*settings.output_price for u in usage)/1e6
    return {'mode':settings.app_mode,'label':'Datos de demostración' if settings.app_mode=='demo' else 'Datos de proveedores externos',
        'cutoff':cutoff,'selections':results,'warnings':dependencies(request.selections),
        'joint_probability':None,'analyst_comment':analyst,'ai':settings.ai_summary(),'usage':usage,'estimated_cost_usd':cost,'price_date':settings.price_date or None,
        'final_result':None,'conclusion':'Sin ventaja demostrada' if all(c.get('event') for c in contexts) else 'Datos insuficientes'}


async def run_job(job_id):
    with Session.begin() as db:
        job=db.get(Job,job_id)
        if not job: return
        job.status='running';request=AnalysisRequest.model_validate_json(job.request)
    try:
        report=await asyncio.wait_for(build_report(request,job_id),settings.max_analysis_seconds)
        with Session.begin() as db:
            job=db.get(Job,job_id)
            if job: job.status='completed';job.report=json.dumps(report,ensure_ascii=False)
    except asyncio.CancelledError:
        with Session.begin() as db:
            job=db.get(Job,job_id)
            if job: job.status='interrupted';job.error='Proceso detenido. Se conserva la solicitud.'
        raise
    except Exception as e:
        with Session.begin() as db:
            job=db.get(Job,job_id)
            if job: job.status='failed';job.error='Tiempo de análisis agotado.' if isinstance(e,TimeoutError) else 'No se pudo completar el análisis. Revisa los datos.'
