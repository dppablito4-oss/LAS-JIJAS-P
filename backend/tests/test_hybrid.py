import asyncio
import copy
import json
from datetime import datetime,timezone,timedelta
from types import SimpleNamespace as NS
import pytest
from app import llm,service,providers,model
from app.config import Settings,settings
from app.schemas import Selection,AnalysisRequest,Evidence
from test_profiles import Dump,Box,configure


def test_hybrid_template_is_accepted():
    s=Settings(_env_file='.env.example',app_mode='real',openai_api_key='fake',deepseek_api_key='fake')
    assert s.ai_profile=='hybrid' and s.vision_model=='gpt-6-luna' and s.analyst_model=='deepseek-v4-pro'
    assert s.review_enabled and s.review_effort=='high'
    assert s.token_limit('vision')==4096 and s.token_limit('review')==8192 and s.token_limit('deepseek')==8192
    assert s.max_output_tokens==8192 and s.max_analysis_seconds==240
    assert s.model_timeout_seconds==45 and s.ai_timeout_seconds==90


@pytest.mark.parametrize('mode,effort',[('standard','high'),('pro','max')])
def test_reviewer_preserves_engine_and_uses_bounded_preset(monkeypatch,mode,effort):
    configure(monkeypatch,'hybrid')
    monkeypatch.setattr(settings,'openai_review_enabled',True)
    monkeypatch.setattr(settings,'openai_review_mode',mode)
    monkeypatch.setattr(settings,'openai_review_effort','high')
    monkeypatch.setattr(settings,'review_max_tokens',8192)
    requests=[];ledger=[]
    async def create(**kwargs):
        requests.append(kwargs)
        return NS(status='completed',usage=Dump({'input_tokens':10,'output_tokens':7}),
            output_text=json.dumps({'verdict':'issues_found','observations':['Modelo experimental.'],'summary':'Falta validación adicional.'}))
    class Client:
        def __init__(self,**kwargs):self.responses=NS(create=create)
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
    monkeypatch.setattr(llm,'AsyncOpenAI',Client)
    monkeypatch.setattr(llm,'record_usage',lambda *args:ledger.append(args))
    selections=[{'selection':{},'event':{},'market':{'probability':.6,'ev':.2},'warnings':[],
        'conclusion':'Sin ventaja demostrada','model_note':'Experimental',
        'model':{'score_distribution':[[.5,.5]],'status':'experimental'},'evidence':[]}]
    original=copy.deepcopy(selections)
    r=asyncio.run(llm.review_report(selections,'Comentario original','test-job'))
    assert r['status']=='completed' and selections==original
    assert requests[0]['model']=='gpt-6.1-sol' and requests[0]['reasoning']['effort']==effort
    assert requests[0]['max_output_tokens']==8192 and requests[0]['store'] is False
    assert 'tools' not in requests[0] and 'score_distribution' not in requests[0]['input']
    assert ledger[0][:3]==('test-job','openai','gpt-6.1-sol')


def test_disabled_review_does_not_open_a_client(monkeypatch):
    monkeypatch.setattr(settings,'openai_review_enabled',False)
    def forbidden(**kwargs):raise AssertionError('No debe llamar a API')
    monkeypatch.setattr(llm,'AsyncOpenAI',forbidden)
    assert asyncio.run(llm.review_report([],'test'))=={'status':'disabled'}


def test_deepseek_thinking_can_be_disabled(monkeypatch):
    configure(monkeypatch,'hybrid')
    monkeypatch.setattr(settings,'deepseek_thinking',False)
    monkeypatch.setattr(settings,'deepseek_max_tokens',8192)
    requests=[]
    async def create(**kwargs):
        requests.append(kwargs)
        return NS(choices=[NS(message=Dump({'role':'assistant','content':'Respuesta.'}),finish_reason='stop')],usage=None)
    class Client:
        def __init__(self,**kwargs):self.chat=NS(completions=NS(create=create))
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
    monkeypatch.setattr(llm,'AsyncOpenAI',Client)
    assert asyncio.run(llm.analyze(Box(),[]))=='Respuesta.'
    assert requests[0]['extra_body']['thinking']['type']=='disabled'
    assert 'reasoning_effort' not in requests[0] and requests[0]['max_tokens']==8192


def prepare_report(monkeypatch,history_age=1,quote_age=1):
    configure(monkeypatch,'hybrid')
    cutoff=datetime(2026,10,29,12,tzinfo=timezone.utc)
    monkeypatch.setattr(service,'now',lambda:cutoff)
    event=providers.demo_events()[0]
    async def resolve(s):return Evidence(status='ok',source={'provider':'test','reference':'test:event'},data={'candidates':[event.model_dump(mode='json')]})
    async def histories(e,c):return [dict(date=(cutoff-timedelta(days=history_age)).isoformat(),home=e.home,away=e.away,hg=2,ag=0)],'test:history'
    async def context(*args):return {'status':True}
    async def analyze(*args):return 'Comentario fijo.'
    monkeypatch.setattr(providers,'resolve',resolve)
    monkeypatch.setattr(providers,'histories',histories)
    monkeypatch.setattr('app.isolated.query',context)
    monkeypatch.setattr(service,'analyze',analyze)
    monkeypatch.setattr(model,'predict',lambda *args:{'status':'experimental','home_draw_away':[.6,.2,.2]})
    s=Selection(home=event.home,away=event.away,competition=event.competition,starts_at=event.starts_at,event_id=event.id,
                market='1x2',side='home',odds=2,observed_at=cutoff-timedelta(hours=quote_age))
    return AnalysisRequest(reviewed=True,selections=[s])


def test_review_failure_keeps_original_report(monkeypatch):
    request=prepare_report(monkeypatch)
    monkeypatch.setattr(settings,'openai_review_enabled',True)
    async def unavailable(*args):raise TimeoutError()
    monkeypatch.setattr(service,'review_report',unavailable)
    r=asyncio.run(service.build_report(request))
    assert r['review']['status']=='unavailable'
    assert r['analyst_comment']=='Comentario fijo.'
    assert r['selections'][0]['market']['probability']==.6
    assert r['selections'][0]['market']['ev']==pytest.approx(.2)
    assert r['conclusion']=='Sin ventaja demostrada' and r['estimated_cost_usd'] is None


@pytest.mark.parametrize('history_age,quote_age',[(31,1),(1,25),(1,-1)])
def test_freshness_prevents_ev_for_outdated_or_future_inputs(monkeypatch,history_age,quote_age):
    request=prepare_report(monkeypatch,history_age,quote_age)
    monkeypatch.setattr(settings,'max_history_age_days',30)
    monkeypatch.setattr(settings,'max_quote_age_hours',24)
    r=asyncio.run(service.build_report(request))
    assert r['selections'][0]['market']['ev'] is None
    assert r['selections'][0]['market']['implied']==.5
    assert r['selections'][0]['warnings'] and r['conclusion']=='Datos insuficientes'
    if history_age>30: assert r['selections'][0]['model'] is None


def test_model_deadline_cancels_call(monkeypatch):
    monkeypatch.setattr(settings,'model_timeout_seconds',.01)
    cancelled=[]
    async def slow(**kwargs):
        try:await asyncio.sleep(10)
        finally:cancelled.append(True)
    with pytest.raises(TimeoutError):asyncio.run(llm.model_call(slow))
    assert cancelled==[True]
