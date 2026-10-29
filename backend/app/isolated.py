"""Bound third-party synchronous network work with a killable process.

No user-supplied import paths, commands or functions are accepted.
"""
import asyncio
import multiprocessing as mp
import time

OPERATIONS={'football-season','football-context','nba-logs','football-model'}


def _run(connection,kind,value):
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
        elif kind=='football-model':
            from .model import predict
            result=predict(**value)
        else: raise ValueError('Operación no permitida')
        connection.send(('ok',result))
    except Exception:
        connection.send(('error',None))
    finally:
        connection.close()


async def _receive(connection,process,timeout):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        if connection.poll():
            return await asyncio.to_thread(connection.recv)
        if not process.is_alive():
            raise ValueError('El proceso terminó sin respuesta')
        await asyncio.sleep(.02)
    raise TimeoutError('Tiempo de operación agotado')


async def query(kind,value,timeout=18):
    if kind not in OPERATIONS:
        raise ValueError('Operación no permitida')
    context=mp.get_context('spawn')
    reader,writer=context.Pipe(duplex=False)
    process=context.Process(target=_run,args=(writer,kind,value),daemon=True)
    try:
        process.start()
        writer.close()
        status,result=await asyncio.wait_for(_receive(reader,process,timeout),timeout)
        if status!='ok':raise ValueError('Proveedor no disponible')
        return result
    finally:
        if process.pid is not None:
            if process.is_alive():process.terminate()
            process.join(1)
            if process.is_alive():
                process.kill()
                process.join(1)
            process.close()
        reader.close()
        writer.close()
