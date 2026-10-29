import asyncio
from types import SimpleNamespace as NS
from app.config import Settings,settings
from app import llm
from app.schemas import Selection
from app.tools import ToolBox
from test_core import image_bytes


class Dump:
    def __init__(self,value):self.value=value
    def model_dump(self,**kwargs):return self.value


class Box:
    contexts=[{}]
    def __init__(self):self.calls=[]
    def definitions(self):
        return ToolBox([{'selection':Selection()}],'2026-10-29T12:00:00Z').definitions()
    async def call(self,name,args):
        self.calls.append((name,args))
        return {'status':'ok','data':{'wins':3,'n':5}}


def configure(monkeypatch,profile):
    monkeypatch.setattr(settings,'app_mode','real')
    monkeypatch.setattr(settings,'ai_profile',profile)
    monkeypatch.setattr(settings,'openai_single_model','gpt-6.1-sol')
    monkeypatch.setattr(settings,'openai_vision_model','gpt-6-luna')
    monkeypatch.setattr(settings,'deepseek_model','deepseek-flash')
    monkeypatch.setattr(settings,'openai_api_key','fake-test-key')
    monkeypatch.setattr(settings,'deepseek_api_key','fake-test-key')


def test_settings_profiles_and_empty_optional_rates(tmp_path):
    env=tmp_path/'local.env'
    env.write_text('AI_PROFILE=sol\nINPUT_PRICE=\nOUTPUT_PRICE=\nOPENAI_SINGLE_MODEL=\n',encoding='utf-8')
    sol=Settings(_env_file=env,openai_api_key='fake',deepseek_api_key='')
    assert sol.vision_model==sol.analyst_model=='gpt-6.1-sol'
    assert sol.analyst_configured and sol.input_price is None and sol.output_price is None
    economy=Settings(_env_file=None,ai_profile='economy',openai_api_key='',deepseek_api_key='fake')
    assert economy.vision_model=='gpt-6-luna' and economy.analyst_model=='deepseek-flash'
    assert economy.analyst_provider=='deepseek' and economy.analyst_configured
    pro=Settings(_env_file=None,ai_profile='economy',deepseek_model='deepseek-v4-pro')
    assert pro.analyst_model=='deepseek-v4-pro'


def test_sol_analyzer_uses_responses_and_preserves_reasoning(monkeypatch):
    configure(monkeypatch,'sol');monkeypatch.setattr(settings,'deepseek_api_key','')
    requests=[];ledger=[]
    async def create(**kwargs):
        # Copy before the in-memory conversation is extended.
        requests.append({**kwargs,'input':list(kwargs['input'])})
        output=([{'type':'reasoning','id':'rs_1','summary':[],'encrypted_content':'opaque'},
                 {'type':'function_call','id':'fc_1','call_id':'call_original','name':'get_team_form',
                  'arguments':'{"selection_index":0,"window":5,"venue":"all"}'}]
                if len(requests)==1 else [{'type':'message','role':'assistant','content':[{'type':'output_text','text':'Datos insuficientes.'}]}])
        return NS(output=[Dump(v) for v in output],output_text='' if len(requests)==1 else 'Datos insuficientes.',
                  status='completed',usage=Dump({'input_tokens':12,'output_tokens':5}))
    class Client:
        def __init__(self,**kwargs):self.responses=NS(create=create)
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
    monkeypatch.setattr(llm,'AsyncOpenAI',Client)
    monkeypatch.setattr(llm,'record_usage',lambda *args:ledger.append(args))
    box=Box();usage=[]
    assert asyncio.run(llm.analyze(box,usage,'job-test'))=='Datos insuficientes.'
    assert len(requests)==2 and len(box.calls)==1 and len(ledger)==2 and len(usage)==2
    assert all(r['model']=='gpt-6.1-sol' and r['store'] is False for r in requests)
    assert all(t['strict'] for t in requests[0]['tools'])
    assert any(i.get('encrypted_content')=='opaque' for i in requests[1]['input'])
    assert any(i.get('type')=='function_call_output' and i['call_id']=='call_original' for i in requests[1]['input'])
    assert ledger[0][1:3]==('openai','gpt-6.1-sol')


def test_vision_routes_to_each_profile_without_changing_keys(monkeypatch):
    calls=[]
    async def create(**kwargs):
        calls.append(kwargs)
        return NS(status='completed',output_text='{"selections":[]}',usage=Dump({'input_tokens':5,'output_tokens':2}))
    class Client:
        def __init__(self,**kwargs):self.responses=NS(create=create)
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
    monkeypatch.setattr(llm,'AsyncOpenAI',Client)
    monkeypatch.setattr(llm,'record_usage',lambda *args:None)
    for profile,model in [('sol','gpt-6.1-sol'),('economy','gpt-6-luna')]:
        configure(monkeypatch,profile)
        result=asyncio.run(llm.extract(image_bytes()))
        assert result['model']==model and calls[-1]['model']==model
        assert result['extraction']['status']=='needs_review'


def test_economy_analyzer_uses_deepseek_with_thinking(monkeypatch):
    configure(monkeypatch,'economy');monkeypatch.setattr(settings,'openai_api_key','')
    requests=[]
    async def create(**kwargs):
        requests.append({**kwargs,'messages':list(kwargs['messages'])})
        message=({'role':'assistant','reasoning_content':'preserve-this','tool_calls':[
            {'id':'deepseek-call','type':'function','function':{'name':'get_team_form','arguments':'{"selection_index":0}'}}]}
            if len(requests)==1 else {'role':'assistant','content':'Comentario final.'})
        return NS(choices=[NS(message=Dump(message),finish_reason='tool_calls' if len(requests)==1 else 'stop')],usage=Dump({'prompt_tokens':10,'completion_tokens':4}))
    clients=[]
    class Client:
        def __init__(self,**kwargs):
            clients.append(kwargs);self.chat=NS(completions=NS(create=create))
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
    monkeypatch.setattr(llm,'AsyncOpenAI',Client)
    monkeypatch.setattr(llm,'record_usage',lambda *args:None)
    assert asyncio.run(llm.analyze(Box(),[]))=='Comentario final.'
    assert clients[0]['base_url']=='https://api.deepseek.com'
    assert requests[0]['model']=='deepseek-flash'
    assert requests[0]['extra_body']['thinking']['type']=='enabled'
    assert requests[0]['reasoning_effort']=='high'
    assert requests[1]['messages'][2]['reasoning_content']=='preserve-this'
    assert requests[1]['messages'][3]['tool_call_id']=='deepseek-call'


def test_responses_incomplete_preserves_usage_without_executing_tools():
    async def complete(*args):
        return {'status':'incomplete','output':[],'usage':{'input_tokens':3,'output_tokens':4}}
    usage=[];box=Box()
    result=asyncio.run(llm.responses_loop(complete,box,usage))
    assert 'Límite' in result and len(usage)==1 and not box.calls
