import asyncio
import io
import json
from datetime import datetime, timezone, timedelta
import pytest
from PIL import Image
from pydantic import ValidationError
from app.analytics import evaluate, dependencies, form
from app.schemas import Selection, AnalysisRequest
from app import providers
from app.llm import extract, normalize_image, tool_loop
from app.tools import ToolBox
from app.model import predict
from app.config import settings
from app.db import init, Session, Cache, Job, engine


@pytest.fixture(autouse=True)
def demo(monkeypatch):
    monkeypatch.setattr(settings,'app_mode','demo')
    init()


def test_odds_and_complete_market():
    s=Selection(odds='2,00',side='home',complete_market={'home':2,'draw':3,'away':4})
    r=evaluate(s,.6)
    assert r['implied']==.5
    assert r['ev']==pytest.approx(.2)
    assert sum(r['reference'].values())==pytest.approx(1)
    assert r['margin']==pytest.approx(1/12)
    assert evaluate(s)['ev'] is None
    assert evaluate(s.model_copy(update={'complete_market':{'home':2}}))['reference'] is None


@pytest.mark.parametrize('odds',[1,0,-1,'ilegible','NaN','Infinity'])
def test_invalid_odds(odds):
    with pytest.raises(ValidationError): Selection(odds=odds)


@pytest.mark.parametrize('line',[2,2.25,2.75])
def test_push_and_quarter_lines(line):
    r=evaluate(Selection(market='total',line=line,side='over',odds=2),.6)
    assert r['status']=='unsupported' and r['ev'] is None and r['probability'] is None


def test_scope_and_dependence():
    assert evaluate(Selection(period='first-half',odds=2,side='home'),.6)['ev'] is None
    assert evaluate(Selection(sport='nba',market='moneyline',odds=2,side='home'))['probability'] is None
    warnings=dependencies([Selection(event_id='e',side='home'),Selection(event_id='e',side='away')])
    assert any('incompatibles' in w for w in warnings)


def image_bytes():
    b=io.BytesIO();Image.new('RGB',(100,100)).save(b,format='PNG');return b.getvalue()


def test_extraction_incomplete_and_normalization():
    from app.schemas import Extraction
    e=Extraction.model_validate({'selections':[{'odds':None,'ambiguous_fields':['odds','date']}]})
    assert e.status=='needs_review' and e.selections[0].starts_at is None
    r=asyncio.run(extract(image_bytes()))
    assert r['extraction']['status']=='needs_review'
    assert r['extraction']['selections'][0]['odds']==2.1
    assert 'simulado' in r['extraction']['warnings'][0]
    with pytest.raises(ValueError): normalize_image(b'not an image')
    with pytest.raises(ValueError): normalize_image(b'x'*(settings.max_image_bytes+1))
    assert not Image.open(io.BytesIO(normalize_image(image_bytes()))).getexif()


def test_timezones_and_resolution():
    a=Selection(starts_at='2026-11-01T15:00:00-05:00')
    b=Selection(starts_at='2026-11-01T20:00:00Z')
    assert a.starts_at==b.starts_at
    with pytest.raises(ValidationError): Selection(starts_at='2026-11-01T15:00:00')
    e=asyncio.run(providers.resolve(Selection(home='Lima Azul',away='Puerto Verde',starts_at=a.starts_at,competition='Premier League')))
    assert len(e.data['candidates'])==1
    wrong=asyncio.run(providers.resolve(Selection(home='Lima Azul',starts_at='2026-11-02T20:00:00Z')))
    assert not wrong.data['candidates']


def test_same_names_different_events(monkeypatch):
    from app.schemas import Event
    e=providers.demo_events()[0]
    second=e.model_copy(update={'id':'other','season':'other','starts_at':e.starts_at+timedelta(days=7)})
    monkeypatch.setattr(providers,'demo_events',lambda:[e,second])
    r=asyncio.run(providers.resolve(Selection(home=e.home,away=e.away)))
    assert len(r.data['candidates'])==2


def test_cache_expiry_and_failure(monkeypatch):
    calls=[]
    async def fetch(): calls.append(1);return {'value':1}
    key='test-expiry'
    with Session.begin() as db:
        db.merge(Cache(key=key,expires='2000-01-01T00:00:00+00:00',value='{"value":0}'))
    assert asyncio.run(providers.cached(key,fetch))['value']==1
    assert asyncio.run(providers.cached(key,fetch))['value']==1 and len(calls)==1
    async def fail(): raise TimeoutError()
    with pytest.raises(TimeoutError): asyncio.run(providers.cached('fail-'+str(datetime.now()),fail))
    monkeypatch.setattr(settings,'app_mode','real')
    async def unavailable(*args): raise TimeoutError()
    monkeypatch.setattr(providers,'get_json',unavailable)
    with pytest.raises(TimeoutError): asyncio.run(providers.resolve(Selection(competition='LaLiga',starts_at='2040-01-01T00:00:00Z')))


def test_form_no_future():
    rows=[dict(date='2026-01-01T00:00:00+00:00',home='a',away='b',hg=1,ag=0),dict(date='2027-01-01T00:00:00+00:00',home='a',away='b',hg=7,ag=0)]
    assert form(rows,'a','2026-10-29T00:00:00+00:00')['n']==1


def test_tool_loop_ids_reasoning_and_dedup(monkeypatch):
    class Box:
        contexts=[{}]
        def definitions(self): return []
        async def call(self,name,args):
            if name!='allowed' or args!={}: raise ValueError()
            count.append(1);return {'status':'ok'}
    count=[];messages_seen=[]
    async def complete(messages,tools):
        messages_seen.append(json.loads(json.dumps(messages)))
        if len(messages_seen)==1:
            return {'message':{'role':'assistant','reasoning_content':'preserve-in-memory','tool_calls':[
                {'id':'a','type':'function','function':{'name':'allowed','arguments':'{}'}},
                {'id':'b','type':'function','function':{'name':'allowed','arguments':'{}'}},
                {'id':'c','type':'function','function':{'name':'shell','arguments':'{}'}}]},'usage':{'prompt_tokens':3}}
        return {'message':{'role':'assistant','content':'Datos insuficientes.'}}
    usage=[]
    result=asyncio.run(tool_loop(complete,Box(),usage))
    assert result=='Datos insuficientes.' and count==[1]
    assert [m['tool_call_id'] for m in messages_seen[-1] if m['role']=='tool']==['a','b','c']
    assert messages_seen[-1][2]['reasoning_content']=='preserve-in-memory'
    assert len(usage)==1
    box=ToolBox([{'selection':Selection(),'resolution':{},'market':{}}],'2026-10-29T00:00:00+00:00')
    with pytest.raises(ValueError):asyncio.run(box.call('get_team_form',{'selection_index':0,'url':'http://evil'}))
    with pytest.raises(ValueError):asyncio.run(box.call('execute_sql',{'selection_index':0}))


def test_tool_round_limit(monkeypatch):
    monkeypatch.setattr(settings,'max_tool_rounds',2)
    class Box:
        contexts=[{}]
        def definitions(self): return []
        async def call(self,*a): return {}
    calls=[]
    async def complete(*a):
        calls.append(1)
        return {'message':{'role':'assistant','tool_calls':[{'id':str(len(calls)),'function':{'name':'x','arguments':'{}'}}]}}
    assert 'Límite' in asyncio.run(tool_loop(complete,Box(),[])) and len(calls)==2


def test_model_temporal_evaluation():
    rows=providers.demo_rows()
    cutoff='2026-10-29T12:00:00+00:00'
    result=predict(rows+[dict(date='2027-01-01T00:00:00+00:00',home='Lima Azul',away='Puerto Verde',hg=100,ag=0)],'Lima Azul','Puerto Verde',cutoff)
    assert result['sample_n']==160 and result['sample_to']<cutoff
    assert sum(result['home_draw_away'])==pytest.approx(1)
    assert result['evaluation']['n']>0
    assert result['evaluation']['train_to']<result['evaluation']['from']
    assert result['evaluation']['baseline_log_loss']>0
    assert sum(map(sum,result['score_distribution']))==pytest.approx(1)
