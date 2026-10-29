"""Bound third-party synchronous network work with a killable process.

No user-supplied import paths, commands or functions are accepted.
"""
import asyncio
import multiprocessing as mp


def _run(queue,kind,value):
    try:
        if kind=='football-season':
            from sports_skills import football
            result=football.get_season_schedule(season_id=value)
        elif kind=='football-context':
            from sports_skills import football
            result=football.get_event_summary(event_id=value)
        elif kind=='nba-logs':
            from nba_api.stats.endpoints import leaguegamelog
            result=leaguegamelog.LeagueGameLog(season=value,timeout=10).get_normalized_dict()
        else: raise ValueError('Operación no permitida')
        queue.put(('ok',result))
    except Exception:
        queue.put(('error',None))


async def query(kind,value,timeout=18):
    context=mp.get_context('spawn')
    queue=context.Queue()
    process=context.Process(target=_run,args=(queue,kind,value),daemon=True)
    process.start()
    try:
        status,result=await asyncio.wait_for(asyncio.to_thread(queue.get,True,timeout),timeout+1)
        if status!='ok':raise ValueError('Proveedor no disponible')
        return result
    except Exception as e:
        raise TimeoutError('Proveedor no disponible o tiempo agotado') from e
    finally:
        if process.is_alive():process.terminate()
        await asyncio.to_thread(process.join,2)
        queue.close()
