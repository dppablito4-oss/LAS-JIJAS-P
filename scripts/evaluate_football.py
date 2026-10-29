"""Optional live integration validation; no AI or billable calls."""
import os
os.environ['DATABASE_URL']='sqlite:///data/evaluation.db'
import asyncio
import json
from pathlib import Path
from app.config import settings
from app.db import init
from app.schemas import Selection,Event,now
from app.providers import resolve,histories
from app.model import predict


async def main():
    settings.app_mode='real';init()
    cutoff=now().isoformat()
    result={'retrieved_at':cutoff,'status':'unavailable'}
    try:
        evidence=await resolve(Selection(competition='Premier League',starts_at='2026-11-01T20:00:00Z'))
        event=next(Event.model_validate(e) for e in evidence.data['candidates'] if Event.model_validate(e).starts_at>now())
        rows,reference=await histories(event,cutoff)
        prediction=await asyncio.to_thread(predict,rows,event.home,event.away,cutoff)
        result.update(status=prediction['status'],event=event.model_dump(mode='json'),source=reference,
                      historical_n=len(rows),model={k:v for k,v in prediction.items() if k!='score_distribution'})
    except Exception as e:
        result['error_type']=type(e).__name__
    Path('docs/MODEL_EVALUATION.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(result,indent=2,ensure_ascii=False))


if __name__=='__main__':asyncio.run(main())
