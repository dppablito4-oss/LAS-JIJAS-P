import io
import time
import uuid
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.config import settings
from app.db import Session,Job,init
from app.schemas import AnalysisRequest
from app.service import build_report
from app import providers
from PIL import Image


def demo_request():
    e=providers.demo_events()[0]
    return {'reviewed':True,'selections':[{'sport':e.sport,'competition':e.competition,'home':e.home,'away':e.away,'starts_at':e.starts_at.isoformat(),
            'event_id':e.id,'market':'total','side':'over','line':2.5,'odds':'1,95','observed_at':'2026-10-29T00:00:00Z'}]}


def test_demo_e2e_history_persistence_idempotency(monkeypatch):
    monkeypatch.setattr(settings,'app_mode','demo')
    with TestClient(app) as client:
        assert client.get('/api/health').json()['mode']=='demo'
        b=io.BytesIO();Image.new('RGB',(100,100)).save(b,format='PNG')
        extraction=client.post('/api/tickets/extract',files={'file':('test.png',b.getvalue(),'image/png')})
        assert extraction.status_code==200
        s=extraction.json()['extraction']['selections'][0]
        candidates=client.post('/api/events/resolve',json=s).json()['data']['candidates']
        assert candidates[0]['id']=='demo-football-1'
        body=demo_request();key=str(uuid.uuid4());headers={'Idempotency-Key':key}
        a=client.post('/api/analyses',json=body,headers=headers)
        assert a.status_code==202,a.text
        jid=a.json()['id']
        assert client.post('/api/analyses',json=body,headers=headers).json()['id']==jid
        for _ in range(100):
            job=client.get('/api/analyses/'+jid).json()
            if job['status'] not in ['queued','running']:break
            time.sleep(.1)
        assert job['status']=='completed',job
        assert job['report']['selections'][0]['market']['probability'] is not None
        assert job['report']['label']=='Datos de demostración'
        assert job['report']['selections'][0]['model']['evaluation']['n']>0
        assert any(j['id']==jid for j in client.get('/api/analyses').json())
        body['selections'][0]['odds']=3
        assert client.post('/api/analyses',json=body,headers=headers).status_code==409
        body['parent_id']=jid
        revision=client.post('/api/analyses',json=body,headers={'Idempotency-Key':str(uuid.uuid4())}).json()
        assert revision['id']!=jid
    with TestClient(app) as client:
        assert client.get('/api/analyses/'+jid).json()['report']==job['report']
        assert client.delete('/api/analyses/'+jid).json()['deleted']


def test_recovery_of_interrupted_job():
    jid=str(uuid.uuid4())
    with Session.begin() as db:
        db.add(Job(id=jid,key=jid,digest='x',created_at='2026-10-29T00:00:00+00:00',status='running',request='{}'))
    init()
    with Session() as db: assert db.get(Job,jid).status=='interrupted'


def test_real_missing_configuration_and_partial_provider(monkeypatch):
    monkeypatch.setattr(settings,'app_mode','real')
    monkeypatch.setattr(settings,'openai_api_key','')
    monkeypatch.setattr(settings,'deepseek_api_key','')
    async def unavailable(s): return providers.unavailable('ESPN','Timeout')
    monkeypatch.setattr(providers,'resolve',unavailable)
    r=asyncio.run(build_report(AnalysisRequest.model_validate(demo_request())))
    assert r['mode']=='real' and r['conclusion']=='Datos insuficientes'
    assert r['selections'][0]['market']['ev'] is None
    assert r['selections'][0]['resolution']['status']=='unavailable'
    assert 'fixture:' not in str(r)


def test_real_provider_failure_keeps_price_only(monkeypatch):
    monkeypatch.setattr(settings,'app_mode','demo')
    async def failure(*a): raise TimeoutError()
    monkeypatch.setattr(providers,'histories',failure)
    r=asyncio.run(build_report(AnalysisRequest.model_validate(demo_request())))
    assert r['selections'][0]['market']['implied']>0
    assert r['selections'][0]['market']['ev'] is None
    assert r['selections'][0]['evidence'][0]['status']=='unavailable'


def test_missing_vision_config_and_origin(monkeypatch):
    monkeypatch.setattr(settings,'app_mode','real')
    monkeypatch.setattr(settings,'openai_api_key','')
    monkeypatch.setattr(settings,'openai_vision_model','')
    with TestClient(app) as client:
        b=io.BytesIO();Image.new('RGB',(100,100)).save(b,format='PNG')
        response=client.post('/api/tickets/extract',files={'file':('test.png',b.getvalue(),'image/png')})
        assert response.status_code==422 and 'Configura' in response.json()['detail']
        assert client.get('/api/health',headers={'Origin':'https://evil.example'}).status_code==403
        assert client.get('/api/capabilities').json()['vision_configured'] is False


def test_idempotency_without_dynamic_defaults(monkeypatch):
    monkeypatch.setattr(settings,'app_mode','demo')
    with TestClient(app) as client:
        body=demo_request();del body['selections'][0]['observed_at']
        headers={'Idempotency-Key':str(uuid.uuid4())}
        a=client.post('/api/analyses',json=body,headers=headers)
        b=client.post('/api/analyses',json=body,headers=headers)
        assert a.status_code==b.status_code==202
        assert a.json()['id']==b.json()['id']
