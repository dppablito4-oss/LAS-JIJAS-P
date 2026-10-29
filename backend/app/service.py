import asyncio
import json
from datetime import datetime
from .schemas import AnalysisRequest, Event, now
from .config import settings
from .db import Session, Job
from . import providers
from .analytics import evaluate, dependencies
from .tools import ToolBox
from .llm import analyze, review_report
from .isolated import query


async def build_report(request,scope='analysis'):
    deadline=asyncio.get_running_loop().time()+settings.max_analysis_seconds-2
    cutoff='2026-10-29T12:00:00+00:00' if settings.app_mode=='demo' else now().isoformat()
    contexts=[];results=[];usage=[];models={}
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
                    if rows and (datetime.fromisoformat(cutoff)-c['data_as_of']).total_seconds()>settings.max_history_age_days*86400:
                        c['stale_history']=True
                        c['history_stale']=True
                        c['warnings'].append(f'Históricos con más de {settings.max_history_age_days} días de antigüedad; probabilidad aplicable y EV suspendidos.')
                except Exception:
                    c['warnings'].append('Fuente histórica no disponible o timeout. No se utilizaron datos demo.')
                if s.sport=='football' and c.get('rows') and not c.get('stale_history'):
                    try:
                        if event.id not in models:
                            payload={'rows':c['rows'],'home':event.home,'away':event.away,'cutoff':cutoff,'xi':settings.model_xi,
                                     'total_lines':[x.line for x in request.selections if x.event_id==event.id and x.market=='total' and x.line is not None]}
                            if settings.app_mode=='real':payload.update(home_id=event.home_id,away_id=event.away_id)
                            models[event.id]=await query('football-model',payload,settings.model_timeout_seconds)
                        c['model']=models[event.id]
                    except Exception:
                        c['model']={'status':'unavailable','reason':'El ajuste no se completó o superó el límite de tiempo.'}
                if s.sport=='football' and settings.app_mode=='real':
                    # Only the public read-only summary module is called; no trading modules.
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
        if settings.app_mode=='real':
            instant=datetime.fromisoformat(cutoff)
            c['quote_age_hours']=(instant-s.observed_at).total_seconds()/3600
            c['quote_stale']=bool(s.observed_at>instant or s.starts_at and s.observed_at>=s.starts_at or c['quote_age_hours']>settings.max_quote_age_hours)
            if s.observed_at>instant or s.starts_at and s.observed_at>=s.starts_at:
                c['warnings'].append('Cuota posterior al corte o al inicio: EV suspendido.')
                p=None
            elif (instant-s.observed_at).total_seconds()>settings.max_quote_age_hours*3600:
                c['warnings'].append('Cuota antigua: vuelve a comprobar el precio; EV suspendido.')
                p=None
            if c.get('stale_history'):p=None
        c['market']=evaluate(s,p)
        c['warnings'].extend(c['market']['warnings'])
        if s.market=='total' and c['market']['status']=='unsupported':
            c['warnings'].append('Totales modelables: partido completo, de 0,5 a 9,5 goles, solo medios goles.')
        contexts.append(c)
    box=ToolBox(contexts,cutoff)
    for i,c in enumerate(contexts):
        s=c['selection'];ev=c.get('event')
        toolnames=['get_team_form','get_match_context','get_football_stats' if s.sport=='football' else 'get_nba_stats']
        evidence=[await box.call(n,{'selection_index':i}) for n in toolnames]
        results.append({'selection':s.model_dump(mode='json'),'event':ev.model_dump(mode='json') if ev else None,
            'resolution':c['resolution'],'market':c['market'],'model':c.get('model'),
            'evidence':evidence,'warnings':c['warnings'],
            'quote_age_hours':c.get('quote_age_hours'),
            'conclusion':'Datos insuficientes' if not ev or not c.get('rows') or c.get('stale_history') or c.get('quote_stale') else 'Sin ventaja demostrada',
            'model_note':'Modelo experimental; EV orientativo, sin ventaja validada.' if c.get('model',{}).get('status')=='experimental' else 'Sin probabilidad propia sustentada. NBA: análisis descriptivo.' if s.sport=='nba' else 'Modelo no disponible.'})
    analyst='Demo: explicación determinista; no se consultó IA.'
    review={'status':'disabled','model':settings.openai_review_model}
    if settings.app_mode=='real':
        ai_deadline=min(deadline,asyncio.get_running_loop().time()+settings.ai_timeout_seconds)
        remaining=ai_deadline-asyncio.get_running_loop().time()
        stages=2 if settings.review_enabled and settings.openai_api_key else 1
        try:
            if remaining<=0:raise TimeoutError()
            analyst=await asyncio.wait_for(analyze(box,usage,scope),remaining/stages)
        except Exception:analyst='Analista no disponible o timeout. Se conserva el informe y el uso conocido.'
        if settings.review_enabled:
            try:
                remaining=ai_deadline-asyncio.get_running_loop().time()
                if remaining<=0:raise TimeoutError()
                review=await asyncio.wait_for(review_report(results,analyst,usage,scope),remaining)
            except Exception:review={'status':'unavailable','model':settings.openai_review_model,'reason':'Timeout o fallo de revisión. Se conserva el informe original.'}
    review_legacy={'status':'ok' if review['status']=='completed' else review['status'],
                   'model':review.get('model',settings.openai_review_model),
                   'comment':review.get('result',{}).get('summary',review.get('reason',''))}
    cost=None
    analyst_usage=[u for u in usage if u.get('stage')!='review']
    if not usage: cost=0 if settings.app_mode=='demo' else None
    elif (analyst_usage and settings.price_model==settings.analyst_model and all(u.get('provider')==settings.analyst_provider and u.get('model')==settings.price_model for u in analyst_usage)
          and settings.input_price is not None and settings.output_price is not None and settings.price_date):
        cost=sum(u.get('prompt_tokens',u.get('input_tokens',0))*settings.input_price+u.get('completion_tokens',u.get('output_tokens',0))*settings.output_price for u in analyst_usage)/1e6
    return {'mode':settings.app_mode,'label':'Datos de demostración' if settings.app_mode=='demo' else 'Datos de proveedores externos',
        'cutoff':cutoff,'selections':results,'warnings':dependencies(request.selections),
        'joint_probability':None,'analyst_comment':analyst,'ai':settings.ai_summary(),'ai_review':review_legacy,'review':review,'usage':usage,'estimated_cost_usd':cost if review['status']=='disabled' else None,'analyst_estimated_cost_usd':cost,'price_date':settings.price_date or None,
        'final_result':None,'conclusion':'Datos insuficientes' if any(r['conclusion']=='Datos insuficientes' for r in results) else 'Sin ventaja demostrada'}


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
