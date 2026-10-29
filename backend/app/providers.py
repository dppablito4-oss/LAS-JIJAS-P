"""Read-only providers. Never replace failed live requests with demo values."""
import asyncio
import csv
import io
import json
import random
from datetime import datetime, timedelta, timezone
import httpx
from .isolated import query
from .schemas import Event, Evidence, Selection, now
from .config import settings
from .db import Session, Cache

LEAGUES = {'Premier League': ('soccer/eng.1', 'E0'), 'LaLiga': ('soccer/esp.1', 'SP1'), 'NBA': ('basketball/nba', None)}


async def cached(key, fetch, ttl=3600):
    with Session() as db:
        row = db.get(Cache, key)
        if row and datetime.fromisoformat(row.expires) > now():
            return json.loads(row.value)
    value = await fetch()
    value['_retrieved_at']=now().isoformat()
    with Session.begin() as db:
        db.merge(Cache(key=key, expires=(now()+timedelta(seconds=ttl)).isoformat(), value=json.dumps(value)))
    return value


async def get_json(url):
    async with httpx.AsyncClient(timeout=12, follow_redirects=True) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.json()


def demo_events():
    return [Event(id='demo-football-1', sport='football', competition='Premier League', season='sintética-2026',
                  starts_at=datetime(2026,11,1,20,tzinfo=timezone.utc), home='Lima Azul', away='Puerto Verde',
                  home_id='lima',away_id='puerto',provider='demo-synthetic',reference='fixture:demo-football-1'),
            Event(id='demo-nba-1',sport='nba',competition='NBA',season='sintética-2026',
                  starts_at=datetime(2026,11,2,1,tzinfo=timezone.utc),home='Cóndores',away='Delfines',
                  home_id='condores',away_id='delfines',provider='demo-synthetic',reference='fixture:demo-nba-1')]


def demo_rows(sport='football'):
    rng = random.Random(31)
    teams = ['Lima Azul','Puerto Verde','Sol Norte','Costa Roja','Valle Oro','Sierra Blanca'] if sport=='football' else ['Cóndores','Delfines','Pumas','Halcones']
    rows = []
    for day in range(160):
        a,b = rng.sample(teams,2)
        hg,ag = (rng.randint(0,4),rng.randint(0,3)) if sport=='football' else (rng.randint(85,130),rng.randint(85,130))
        rows.append(dict(date=(datetime(2026,5,1,tzinfo=timezone.utc)+timedelta(days=day)).isoformat(),home=a,away=b,hg=hg,ag=ag))
    return rows


async def resolve(s: Selection):
    if settings.app_mode == 'demo':
        events = [e for e in demo_events() if e.sport == s.sport and (not s.competition or e.competition==s.competition)]
        events = [e for e in events if (not s.home or s.home.casefold() in e.home.casefold()) and (not s.away or s.away.casefold() in e.away.casefold())]
        if s.starts_at:
            events = [e for e in events if abs((e.starts_at-s.starts_at).total_seconds())<=300]
        return Evidence(status='ok' if events else 'needs_review', source={'provider':'demo-synthetic','reference':'fixture:events'},
                        data={'candidates':[e.model_dump(mode='json') for e in events]},warnings=['Datos de demostración: eventos ficticios.'])
    if s.competition not in LEAGUES or not s.starts_at:
        return Evidence(status='needs_review',source={'provider':'ESPN','reference':None},
                        missing_fields=['competition','starts_at'],warnings=['Selecciona competición y fecha con zona horaria.'])
    slug,_ = LEAGUES[s.competition]
    if (s.sport == 'nba') != (s.competition == 'NBA'):
        return Evidence(status='unsupported',source={'provider':'ESPN','reference':None},warnings=['Deporte y competición incompatibles.'])
    # Search UTC days on either side, since the entered time may be midnight in Lima.
    dates = [(s.starts_at+timedelta(days=n)).strftime('%Y%m%d') for n in [-1,0,1]]
    events = []
    retrieved=[]
    for day in dates:
        url=f'https://site.api.espn.com/apis/site/v2/sports/{slug}/scoreboard?dates={day}&limit=100'
        raw=await cached('espn:'+slug+':'+day,lambda u=url:get_json(u),300)
        if raw.get('_retrieved_at'): retrieved.append(datetime.fromisoformat(raw['_retrieved_at']))
        for e in raw.get('events',[]):
            c=e['competitions'][0]; competitors=c['competitors']
            h=next(x for x in competitors if x['homeAway']=='home'); a=next(x for x in competitors if x['homeAway']=='away')
            home=h['team']['displayName']; away=a['team']['displayName']
            if s.home and s.home.casefold() not in home.casefold(): continue
            if s.away and s.away.casefold() not in away.casefold(): continue
            season=str(e.get('season',raw.get('season',{})).get('year','unknown'))
            if s.sport=='nba':
                start=datetime.fromisoformat(e['date'].replace('Z','+00:00'))
                season=str(start.year if start.month>=7 else start.year-1)
            events.append(Event(id=f'espn:{slug}:{e["id"]}',sport=s.sport,competition=s.competition,
                season=season,starts_at=e['date'],home=home,away=away,
                home_id=h['team']['id'],away_id=a['team']['id'],provider='ESPN',reference=url))
    unique={e.id:e for e in events}
    return Evidence(status='partial' if unique else 'needs_review',retrieved_at=min(retrieved) if retrieved else now(),source={'provider':'ESPN','reference':f'https://site.api.espn.com/apis/site/v2/sports/{slug}/scoreboard'},
        data={'candidates':[e.model_dump(mode='json') for e in unique.values()]},warnings=['Cobertura de calendario no garantizada. Verifica categoría, temporada y hora.'])


async def histories(event: Event, cutoff):
    if settings.app_mode=='demo':
        return demo_rows(event.sport), 'fixture:synthetic-history'
    if event.sport=='nba':
        async def fetch():
            season=int(event.season)
            season_str=f'{season}-{str(season+1)[-2:]}'
            return await query('nba-logs',season_str,12)
        raw=await cached('nba:logs:'+event.season+':'+cutoff[:10],fetch,3600)
        games={}
        for r in raw.get('LeagueGameLog',[]): games.setdefault(r['GAME_ID'],[]).append(r)
        rows=[]
        for pair in games.values():
            if len(pair)!=2: continue
            h=next((r for r in pair if 'vs.' in r['MATCHUP']),None)
            a=next((r for r in pair if '@' in r['MATCHUP']),None)
            if not h or not a: continue
            date=datetime.fromisoformat(h['GAME_DATE'].split('T')[0]).replace(tzinfo=timezone.utc)+timedelta(days=1,hours=12)
            # Date-only game logs use next midnight UTC, conservatively excluding same-day results.
            rows.append(dict(date=date.isoformat(),home=h['TEAM_NAME'],away=a['TEAM_NAME'],hg=h['PTS'],ag=a['PTS'],retrieved_at=raw.get('_retrieved_at')))
        return [r for r in rows if r['date']<cutoff], 'https://stats.nba.com/stats/leaguegamelog'
    competition='premier-league' if event.competition=='Premier League' else 'la-liga'
    year=int(event.season)
    rows=[]
    references=[]
    for y in [year-1,year]:
        season_id=f'{competition}-{y}'
        async def fetch(sid=season_id):
            raw=await query('football-season',sid,18)
            if not raw.get('status'): raise ValueError('Fuente hist?rica no disponible')
            return raw
        try:
            raw=await cached('sports-skills:season:'+season_id+':'+cutoff[:10],fetch,21600)
        except (TimeoutError,ValueError):
            continue
        source=raw.get('data',{}).get('source')
        # openfootball does not expose the ESPN team identity namespace.
        # Do not join it to ESPN events by names alone.
        if source=='openfootball': continue
        reference=(f'https://github.com/openfootball/football.json/tree/master/{y}-{y+1}' if source=='openfootball'
            else f'https://site.api.espn.com/apis/site/v2/sports/{LEAGUES[event.competition][0]}/teams/{event.home_id}/schedule?season={y}')
        references.append(reference)
        for r in raw.get('data',{}).get('schedules',[]):
            if r.get('status')!='closed': continue
            if r.get('competition',{}).get('id')!=competition: continue
            date=datetime.fromisoformat(r['start_time'].replace('Z','+00:00'))+timedelta(hours=6)
            if date.isoformat()>=cutoff: continue
            h=next(x['team'] for x in r['competitors'] if x['qualifier']=='home')
            a=next(x['team'] for x in r['competitors'] if x['qualifier']=='away')
            known={event.home_id:event.home,event.away_id:event.away}
            home=known.get(str(h['id']),h['name']);away=known.get(str(a['id']),a['name'])
            scores=r.get('scores',{})
            if scores.get('home') is None or scores.get('away') is None: continue
            rows.append(dict(date=date.isoformat(),home=home,away=away,hg=int(scores['home']),ag=int(scores['away']),
                             home_id=str(h['id']),away_id=str(a['id']),event_id=r['id'],season=season_id,source_reference=reference,retrieved_at=raw.get('_retrieved_at')))
    if not rows: raise ValueError('No hay históricos disponibles')
    return rows, references[-1]



def unavailable(provider, message):
    return Evidence(status='unavailable',source={'provider':provider,'reference':None},warnings=[message])
