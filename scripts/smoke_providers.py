"""Opt-in public sports reads. Does not call an AI API or read API keys."""
import asyncio
import json
import os
from pathlib import Path
os.environ['DATABASE_URL']=os.environ.get('SMOKE_DATABASE_URL','sqlite:///data/smoke.db')
from app.config import settings
from app.db import init
from app.schemas import Selection, Event, now
from app.providers import resolve, histories
from app.isolated import query


async def check(name,fn):
    stamp=now().isoformat()
    try:
        value=await asyncio.wait_for(fn(),45)
        return {'provider':name,'retrieved_at':stamp,'status':'ok',**value}
    except Exception as e:
        return {'provider':name,'retrieved_at':stamp,'status':'unavailable','error_type':type(e).__name__}


async def main():
    settings.app_mode='real';init()
    async def football():
        raw=await query('football-season','premier-league-2025',25)
        data=raw.get('data',{})
        return {'upstream_status':raw.get('status'),'n':len(data.get('schedules',[])),
                'underlying_source':data.get('source','ESPN'),'function':'sports_skills.football.get_season_schedule'}
    async def nba():
        raw=await query('nba-logs','2025-26',12)
        return {'n':len(raw.get('LeagueGameLog',[])),'function':'nba_api.stats.endpoints.leaguegamelog'}
    async def calendar(competition,sport):
        r=await resolve(Selection(competition=competition,sport=sport,starts_at='2026-11-01T20:00:00Z'))
        return {'status':r.status,'n':len(r.data.get('candidates',[])),'reference':r.source['reference']}
    results=await asyncio.gather(check('sports-skills',football),check('nba_api',nba),
        check('ESPN Premier League',lambda:calendar('Premier League','football')),
        check('ESPN LaLiga',lambda:calendar('LaLiga','football')),
        check('ESPN NBA',lambda:calendar('NBA','nba')))
    path=Path('docs/LIVE_SMOKE.json');path.write_text(json.dumps(results,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(results,indent=2,ensure_ascii=False))


if __name__=='__main__': asyncio.run(main())
