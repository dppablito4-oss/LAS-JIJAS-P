"""Check configured model access; --smoke additionally makes bounded billable calls."""
import argparse
import asyncio
import io
import json
import os
import sys
from openai import AsyncOpenAI
# Never interrupt the application's queued/running jobs when initializing smoke tables.
if '--smoke' in sys.argv:
    os.environ['DATABASE_URL']='sqlite:///data/ai-smoke.db'
from app.config import settings


async def check():
    results=[]
    for provider,key,base,models in [
        ('openai',settings.openai_api_key,'https://api.openai.com/v1',list({settings.vision_model,*([settings.analyst_model] if settings.ai_profile=='sol' else []),*([settings.openai_review_model] if settings.ai_profile=='hybrid' and settings.openai_review_enabled else [])})),
        ('deepseek',settings.deepseek_api_key,'https://api.deepseek.com',[settings.deepseek_model])]:
        if not key:
            results.append({'provider':provider,'status':'key_missing'});continue
        try:
            async with AsyncOpenAI(api_key=key,base_url=base,max_retries=0,timeout=20) as client:
                available={model.id async for model in client.models.list()}
            results.append({'provider':provider,'status':'ok','models':{model:model in available for model in models if model}})
        except Exception as error:
            results.append({'provider':provider,'status':'unavailable','error_type':type(error).__name__})
    print(json.dumps({'access':results},ensure_ascii=False,indent=2))


async def smoke():
    from PIL import Image,ImageDraw
    from app import providers
    from app.db import init
    from app.llm import extract,analyze,review_report
    from app.tools import ToolBox
    from app.schemas import Selection,now
    init();settings.app_mode='real'
    usage=[];result={}
    if settings.openai_api_key:
        image=Image.new('RGB',(800,180),'white');ImageDraw.Draw(image).text((20,30),'TEST ONLY: fictional Home vs Away; home win; odds 2.10',fill='black')
        buffer=io.BytesIO();image.save(buffer,format='PNG')
        try:
            response=await asyncio.wait_for(extract(buffer.getvalue()),settings.ai_timeout_seconds)
            result['vision']={'status':'ok','selections':len(response['extraction']['selections'])}
        except Exception as error:result['vision']={'status':'unavailable','error_type':type(error).__name__}
    event=providers.demo_events()[0]
    selection=Selection(home=event.home,away=event.away,event_id=event.id,side='home',odds=2.1)
    context={'selection':selection,'event':event,'rows':providers.demo_rows(),
             'resolution':{'status':'ok','source':{'provider':'synthetic-smoke'},'data':{'candidates':[event.model_dump(mode='json')]}},
             'market':{'status':'unavailable','implied':1/2.1,'probability':None,'ev':None},
             'warnings':['Prueba de integración con datos sintéticos; sin recomendación real.']}
    box=ToolBox([context],now().isoformat())
    try:
        comment=await asyncio.wait_for(analyze(box,usage,'ai-smoke'),settings.ai_timeout_seconds)
        result['analyst']={'status':'ok' if settings.analyst_configured else 'key_missing','model':settings.analyst_model}
    except Exception as error:
        comment='Analista no disponible';result['analyst']={'status':'unavailable','error_type':type(error).__name__}
    try:
        review=await asyncio.wait_for(review_report([],comment,usage,'ai-smoke'),settings.ai_timeout_seconds)
        result['review']={'status':review['status'],'model':review['model']}
    except Exception as error:result['review']={'status':'unavailable','error_type':type(error).__name__}
    print(json.dumps({'synthetic_smoke':result,'completed_api_responses':len(usage),
                      'note':'No certifica calidad OCR ni exactitud deportiva; uso devuelto registrado en SQLite.'},ensure_ascii=False,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--smoke',action='store_true',help='Autoriza llamadas IA facturables con datos sintéticos y límites de .env.')
    arguments=parser.parse_args()
    asyncio.run(check())
    if arguments.smoke:asyncio.run(smoke())
