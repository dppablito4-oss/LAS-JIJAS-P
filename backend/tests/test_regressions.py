import asyncio
import copy
import io
import json
import multiprocessing as mp
import time
from datetime import datetime,timezone
from pathlib import Path
from types import SimpleNamespace
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from app import isolated,providers,llm,service
from app.analytics import evaluate
from app.config import Settings,settings
from app.db import Session,Usage,init
from app.main import app
from app.model import predict
from app.schemas import Selection,AnalysisRequest,Evidence,Event


def test_env_template_loads_and_prices_remain_unknown():
    cfg=Settings(_env_file='.env.example')
    assert cfg.input_price is None and cfg.output_price is None
    assert cfg.openai_vision_model=='gpt-6-luna'
    assert cfg.openai_review_model=='gpt-6.1-sol'
    assert cfg.deepseek_model=='deepseek-v4-pro'


def test_mismatched_complete_market_is_not_used():
    result=evaluate(Selection(odds=3,side='home',complete_market={'home':2,'draw':3,'away':4}),.6)
    assert result['reference'] is None and result['margin'] is None
    assert result['warnings'] and result['ev']==pytest.approx(.8)


def test_requested_total_is_evaluated_and_all_holdout_is_scored():
    result=predict(providers.demo_rows(),'Lima Azul','Puerto Verde','2026-10-29T12:00:00+00:00',total_lines=[6.5])
    assert 0<=result['totals']['6.5']<=1
    evaluation=result['evaluation']
    assert evaluation['n']==32
    assert all(f['train_to']<f['from'] for f in evaluation['folds'])
    assert set(evaluation['calibration_1x2'])=={'home','draw','away'}
    assert evaluation['totals']['6.5']['n']==32
    assert len(result['training_data_sha256'])==64
    assert evaluate(Selection(market='total',line=10.5,side='over',odds=2))['status']=='unsupported'


def test_football_identity_survives_names_changing():
    rows=providers.demo_rows()
    teams=sorted({r[side] for r in rows for side in ['home','away']})
    ids={name:str(index+1) for index,name in enumerate(teams)}
    for index,row in enumerate(rows):
        row.update(home_id=ids[row['home']],away_id=ids[row['away']],provider='ESPN',event_id=str(index))
        row['home']='alias-home-'+str(index);row['away']='alias-away-'+str(index)
    result=predict(rows,'Lima Azul','Puerto Verde','2026-10-29T12:00:00+00:00',home_id=ids['Lima Azul'],away_id=ids['Puerto Verde'])
    assert result['status']=='experimental' and result['sample_n']==160
    rows[0]['provider']='unknown'
    assert predict(rows,'Lima Azul','Puerto Verde','2026-10-29T12:00:00+00:00',home_id=ids['Lima Azul'],away_id=ids['Puerto Verde'])['status']=='unavailable'


def real_event():
    return Event(id='espn:soccer/eng.1:123',sport='football',competition='Premier League',season='2026',
                 starts_at='2030-11-01T20:00:00Z',home='Home',away='Away',home_id='1',away_id='2',provider='ESPN',reference='https://example.test')


def season(source='ESPN'):
    return {'status':True,'data':{'source':source,'schedules':[{'id':'1234','status':'closed','competition':{'id':'premier-league'},
        'start_time':'2026-01-01T00:00:00Z','competitors':[{'qualifier':'home','team':{'id':'1','name':'Alias Home'}},
        {'qualifier':'away','team':{'id':'2','name':'Alias Away'}}],'scores':{'home':1,'away':0}}]}}


def test_provider_namespace_and_deduplication(monkeypatch):
    monkeypatch.setattr(settings,'app_mode','real')
    payload=season()
    async def query(*a):return copy.deepcopy(payload)
    async def cached(key,fetch,ttl):return await fetch()
    monkeypatch.setattr(providers,'query',query);monkeypatch.setattr(providers,'cached',cached)
    rows,_=asyncio.run(providers.histories(real_event(),'2026-10-29T00:00:00+00:00'))
    assert len(rows)==1 and rows[0]['home']=='Home'
    payload['data']['source']='UNKNOWN_NAMESPACE'
    with pytest.raises(ValueError):asyncio.run(providers.histories(real_event(),'2026-10-29T00:00:00+00:00'))


def test_provider_conflicting_duplicates_fail(monkeypatch):
    monkeypatch.setattr(settings,'app_mode','real')
    calls=[]
    async def query(*args):
        payload=season();payload['data']['schedules'][0]['scores']['home']=len(calls)
        calls.append(1);return payload
    async def cached(key,fetch,ttl):return await fetch()
    monkeypatch.setattr(providers,'query',query);monkeypatch.setattr(providers,'cached',cached)
    with pytest.raises(ValueError,match='contradictorios'):
        asyncio.run(providers.histories(real_event(),'2026-10-29T00:00:00+00:00'))


def test_future_quote_rejected_before_queueing(monkeypatch):
    monkeypatch.setattr(settings,'app_mode','real')
    with TestClient(app) as client:
        result=client.post('/api/analyses',headers={'Idempotency-Key':'future-quote-test'},json={'reviewed':True,'selections':[
            {'home':'Home','away':'Away','odds':2,'observed_at':'2099-01-01T00:00:00Z'}]})
        assert result.status_code==422


def test_stale_histories_suspend_ev_and_model_is_reused(monkeypatch):
    monkeypatch.setattr(settings,'app_mode','real')
    event=real_event();calls=[]
    async def resolve(s):return Evidence(status='ok',source={'provider':'ESPN'},data={'candidates':[event.model_dump(mode='json')]})
    async def histories(*a):return [{'date':'2026-01-01T00:00:00+00:00','home':'Home','away':'Away','hg':1,'ag':0}],'https://example.test'
    async def query(kind,payload,timeout):
        calls.append(kind)
        return {'status':'experimental','home_draw_away':[.6,.2,.2],'totals':{'6.5':.1}}
    monkeypatch.setattr(providers,'resolve',resolve);monkeypatch.setattr(providers,'histories',histories);monkeypatch.setattr(service,'query',query)
    selection=Selection(home='Home',away='Away',starts_at=event.starts_at,event_id=event.id,odds=2,side='home')
    report=asyncio.run(service.build_report(AnalysisRequest(reviewed=True,selections=[selection,selection])))
    assert calls.count('football-model')==1
    assert all(s['market']['ev'] is None and s['market']['probability'] is None for s in report['selections'])
    assert any('suspendidos' in w for w in report['selections'][0]['warnings'])


def _blocked(connection,kind,value):
    Path(value).write_text('started',encoding='utf-8')
    time.sleep(60)


def test_model_process_cancelled_after_start(monkeypatch,tmp_path):
    monkeypatch.setattr(isolated,'_run',_blocked)
    marker=tmp_path/'started.txt'
    before={p.pid for p in mp.active_children()}
    async def scenario():
        task=asyncio.create_task(isolated.query('football-model',str(marker),15))
        deadline=time.monotonic()+10
        while not marker.exists() and time.monotonic()<deadline:await asyncio.sleep(.05)
        assert marker.exists(),'Child did not start'
        task.cancel()
        with pytest.raises(asyncio.CancelledError):await task
    asyncio.run(scenario())
    assert {p.pid for p in mp.active_children()}==before


def test_model_process_timeout_reaps_child(monkeypatch,tmp_path):
    monkeypatch.setattr(isolated,'_run',_blocked)
    before={p.pid for p in mp.active_children()}
    with pytest.raises(TimeoutError):asyncio.run(isolated.query('football-model',str(tmp_path/'timeout.txt'),.1))
    assert {p.pid for p in mp.active_children()}==before


class FakeUsage:
    def model_dump(self):return {'input_tokens':10,'output_tokens':5}


class FakeClient:
    calls=[]
    responses_queue=[]
    def __init__(self,**kwargs):self.responses=self;self.chat=SimpleNamespace(completions=self)
    async def __aenter__(self):return self
    async def __aexit__(self,*a):pass
    async def create(self,**kwargs):
        self.calls.append(kwargs)
        return self.responses_queue.pop(0)


def test_openai_vision_and_review_requests_and_usage(monkeypatch):
    monkeypatch.setattr(settings,'app_mode','real');monkeypatch.setattr(settings,'openai_api_key','test-key')
    monkeypatch.setattr(settings,'openai_review_mode','pro')
    monkeypatch.setattr(llm,'AsyncOpenAI',FakeClient)
    FakeClient.calls=[];FakeClient.responses_queue=[
        SimpleNamespace(status='completed',output_text='{"selections":[]}',usage=FakeUsage()),
        SimpleNamespace(status='completed',output_text='Datos insuficientes.',usage=FakeUsage())]
    init();raw=io.BytesIO();Image.new('RGB',(100,100)).save(raw,format='PNG')
    extraction=asyncio.run(llm.extract(raw.getvalue()))
    usage=[];review=asyncio.run(llm.review_report([], 'Sin datos',usage,'test-review'))
    assert extraction['extraction']['status']=='needs_review'
    assert FakeClient.calls[0]['model']=='gpt-6-luna'
    assert FakeClient.calls[0]['store'] is False
    assert FakeClient.calls[1]['model']=='gpt-6.1-sol'
    assert FakeClient.calls[1]['reasoning']=={'effort':'high','mode':'pro'}
    assert review['status']=='ok' and usage[0]['provider']=='openai'
    with Session() as db:assert db.query(Usage).filter_by(scope='test-review',provider='openai').count()==1


def test_deepseek_thinking_request_and_reasoning_persistence(monkeypatch):
    monkeypatch.setattr(settings,'deepseek_api_key','test-key');monkeypatch.setattr(llm,'AsyncOpenAI',FakeClient)
    class Message:
        def model_dump(self,**kwargs):return {'role':'assistant','content':'Sin ventaja demostrada.'}
    FakeClient.calls=[];FakeClient.responses_queue=[SimpleNamespace(usage=FakeUsage(),choices=[SimpleNamespace(message=Message(),finish_reason='stop')])]
    from app.tools import ToolBox
    result=asyncio.run(llm.analyze(ToolBox([],'2026-10-29T00:00:00+00:00'),[],'test-deepseek'))
    assert result=='Sin ventaja demostrada.'
    assert FakeClient.calls[0]['model']=='deepseek-v4-pro'
    assert FakeClient.calls[0]['reasoning_effort']=='high'
    assert FakeClient.calls[0]['extra_body']=={'thinking':{'type':'enabled'}}


def test_review_cannot_mutate_deterministic_report(monkeypatch):
    monkeypatch.setattr(settings,'openai_api_key','test-key');monkeypatch.setattr(llm,'AsyncOpenAI',FakeClient)
    FakeClient.calls=[];FakeClient.responses_queue=[SimpleNamespace(status='incomplete',output_text='partial',usage=FakeUsage())]
    items=[{'selection':{'market':'1x2','odds':2},'market':{'ev':None},'warnings':['EV suspendido'],'model':None,'evidence':[]}]
    before=copy.deepcopy(items)
    result=asyncio.run(llm.review_report(items,'No demostrado',[],'test-incomplete'))
    assert items==before and result['status']=='unavailable'


def test_cost_is_bound_to_active_model_and_review_failure_keeps_report(monkeypatch):
    monkeypatch.setattr(settings,'app_mode','real')
    monkeypatch.setattr(settings,'input_price',1);monkeypatch.setattr(settings,'output_price',2)
    monkeypatch.setattr(settings,'price_date','2026-10-29');monkeypatch.setattr(settings,'price_model','other-model')
    async def resolve(s):return providers.unavailable('ESPN','offline-test')
    async def analyze(box,usage,scope):
        usage.append({'provider':'deepseek','model':settings.deepseek_model,'prompt_tokens':10,'completion_tokens':5})
        return 'Datos insuficientes.'
    async def review(*a):raise TimeoutError()
    monkeypatch.setattr(providers,'resolve',resolve);monkeypatch.setattr(service,'analyze',analyze);monkeypatch.setattr(service,'review_report',review)
    request=AnalysisRequest(reviewed=True,selections=[Selection(home='Home',away='Away',odds=2)])
    report=asyncio.run(service.build_report(request))
    assert report['estimated_cost_usd'] is None and report['selections']
    assert report['ai_review']['status']=='unavailable' and report['conclusion']=='Datos insuficientes'
    monkeypatch.setattr(settings,'price_model',settings.deepseek_model)
    report=asyncio.run(service.build_report(request))
    assert report['estimated_cost_usd']==pytest.approx(.00002)
