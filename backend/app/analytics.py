import math
from .schemas import Selection


def evaluate(s: Selection, probability: float | None = None):
    supported = s.period == 'match' and (
        (s.sport == 'football' and s.market == '1x2' and s.side in ['home', 'draw', 'away'])
        or (s.sport == 'football' and s.market == 'total' and s.side in ['over', 'under']
            and s.line is not None and .5 <= s.line <= 9.5 and s.line % 1 == .5)
        or (s.sport == 'nba' and s.market == 'moneyline' and s.side in ['home', 'away']))
    result = dict(implied=1/s.odds if s.odds else None, reference=None, margin=None,
                  probability=probability if supported else None, ev=None,
                  status='ok' if supported else 'unsupported', warnings=[])
    labels = {'home', 'draw', 'away'} if s.market == '1x2' else {'over', 'under'} if s.market == 'total' else {'home', 'away'}
    if supported and s.complete_market and set(s.complete_market) == labels:
        consistent = s.odds is None or math.isclose(s.complete_market.get(s.side,0),s.odds,rel_tol=1e-9)
        if not consistent:
            result['warnings'].append('La cuota seleccionada no coincide con el mercado completo; referencia sin margen no disponible.')
        elif all(math.isfinite(d) and d > 1 for d in s.complete_market.values()):
            qs = {k: 1/v for k, v in s.complete_market.items()}
            result['margin'] = sum(qs.values()) - 1
            result['reference'] = {k: v/sum(qs.values()) for k, v in qs.items()}
    if supported and probability is None:
        result['status']='unavailable'
    if supported and probability is not None and s.odds:
        if not 0 <= probability <= 1:
            raise ValueError('Probabilidad inválida')
        result['ev'] = probability*s.odds-1
    return result


def dependencies(selections):
    warnings = []
    for i, a in enumerate(selections):
        for b in selections[i+1:]:
            if a.event_id and a.event_id == b.event_id:
                warnings.append('Selecciones del mismo evento: dependencia no modelada.')
                if a.market == b.market == '1x2' and a.side != b.side:
                    warnings.append('Selecciones incompatibles: resultados 1X2 distintos del mismo evento.')
                if a.market == b.market == 'total' and a.side != b.side:
                    over, under = (a,b) if a.side == 'over' else (b,a)
                    if over.line is not None and under.line is not None and over.line >= under.line:
                        warnings.append('Selecciones incompatibles: intervalos de goles excluyentes.')
    if len(selections) > 1:
        warnings.append('No se calcula probabilidad conjunta: independencia no demostrada.')
    return list(dict.fromkeys(warnings))


def form(rows, team, cutoff, window=10, venue='all'):
    eligible = [r for r in rows if r['date'] < cutoff and team in [r['home'], r['away']]
                and (venue == 'all' or r[venue] == team)]
    eligible.sort(key=lambda r:r['date'], reverse=True)
    games = eligible[:window]
    wins = sum((r['hg'] > r['ag'] if r['home'] == team else r['ag'] > r['hg']) for r in games)
    return {'games': games, 'wins': wins, 'n': len(games), 'window': window, 'venue': venue,
            'definition': 'Victorias observadas; no equivalen a probabilidad futura.'}
