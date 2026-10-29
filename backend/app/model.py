"""Dixon-Coles, lazy imports and strictly temporal evaluation."""
import math
from .config import settings


def fit(rows, cutoff):
    import numpy as np
    from datetime import datetime
    from penaltyblog.models import DixonColesGoalModel
    eligible=[r for r in rows if r['date']<cutoff]
    weights=np.array([math.exp(-settings.model_xi*(datetime.fromisoformat(cutoff)-datetime.fromisoformat(r['date'])).total_seconds()/86400) for r in eligible])
    m=DixonColesGoalModel([r['hg'] for r in eligible],[r['ag'] for r in eligible],
                         [r['home'] for r in eligible],[r['away'] for r in eligible],weights=weights)
    m.fit()
    return m


def predict(rows, home, away, cutoff):
    eligible=sorted([r for r in rows if r['date']<cutoff],key=lambda r:r['date'])
    teams=set(r['home'] for r in eligible)|set(r['away'] for r in eligible)
    if len(eligible)<60 or not all(t in teams for t in [home,away]) or any(sum(t in [r['home'],r['away']] for r in eligible)<5 for t in teams):
        return {'status':'unavailable','reason':'Muestra insuficiente o equipos sin identidad histórica verificada.'}
    model=fit(eligible,cutoff)
    grid=model.predict(home,away)
    p=list(map(float,grid.home_draw_away))
    # Fixed temporal holdout, trained once on the earlier block.
    split=int(len(eligible)*.8);train=eligible[:split];test=eligible[split:][-30:]
    evaluation={'status':'experimental','n':0,'reason':'Evaluación pendiente'}
    if len(train)>=45:
        m=fit(train,test[0]['date'])
        counts=[sum((r['hg']>r['ag'],r['hg']==r['ag'],r['hg']<r['ag'])[i] for r in train) for i in range(3)]
        baseline=[(c+1)/(len(train)+3) for c in counts]
        brier=[];logloss=[];bb=[];bl=[];cal=[]
        for r in test:
            try: ps=list(map(float,m.predict(r['home'],r['away']).home_draw_away))
            except (ValueError,KeyError): continue
            target=0 if r['hg']>r['ag'] else 1 if r['hg']==r['ag'] else 2
            brier.append(sum((v-int(i==target))**2 for i,v in enumerate(ps)))
            logloss.append(-math.log(max(ps[target],1e-12)))
            bb.append(sum((v-int(i==target))**2 for i,v in enumerate(baseline)))
            bl.append(-math.log(baseline[target]));cal.append({'p_home':ps[0],'home_won':target==0})
        if brier:
            evaluation={'status':'experimental','n':len(brier),'from':test[0]['date'],'to':test[-1]['date'],
                'train_n':len(train),'train_to':train[-1]['date'],'brier':sum(brier)/len(brier),'log_loss':sum(logloss)/len(logloss),
                'baseline_brier':sum(bb)/len(bb),'baseline_log_loss':sum(bl)/len(bl),
                'calibration': [{'bin':f'{lo/5:.1f}–{(lo+1)/5:.1f}', 'n':len(xs),
                    'mean_p':sum(x['p_home'] for x in xs)/len(xs) if xs else None,
                    'frequency':sum(x['home_won'] for x in xs)/len(xs) if xs else None}
                    for lo in range(5) for xs in [[x for x in cal if lo/5<=x['p_home']<(lo+1)/5]]],
                'reason':'Muestra inicial pequeña, sin certificación de ventaja. Baseline: frecuencias 1X2 del bloque de entrenamiento.'}
    return {'status':'experimental','model':'penaltyblog/DixonColes-1.13.1','xi':settings.model_xi,'cutoff':cutoff,
            'sample_n':len(eligible),'sample_from':eligible[0]['date'],'sample_to':eligible[-1]['date'],
            'home_draw_away':p,'totals':{str(x+.5):float(grid.total_goals('over',x+.5)) for x in range(6)},
            'score_distribution':grid.grid.tolist(),'evaluation':evaluation}
