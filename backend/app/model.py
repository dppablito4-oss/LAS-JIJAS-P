"""Dixon-Coles with stable identities and chronological expanding-window evaluation."""
import hashlib
import json
import math
from datetime import datetime
from statistics import mean, stdev
from .config import settings


def fit(rows, cutoff, xi=None):
    import numpy as np
    from penaltyblog.models import DixonColesGoalModel
    xi=settings.model_xi if xi is None else xi
    eligible=[r for r in rows if r['date']<cutoff]
    weights=np.array([math.exp(-xi*(datetime.fromisoformat(cutoff)-datetime.fromisoformat(r['date'])).total_seconds()/86400) for r in eligible])
    model=DixonColesGoalModel([r['hg'] for r in eligible],[r['ag'] for r in eligible],
                             [r['home'] for r in eligible],[r['away'] for r in eligible],weights=weights)
    model.fit()
    return model


def interval(values):
    """Descriptive normal interval, not a profitability or calibration certificate."""
    if len(values)<2:return None
    delta=1.96*stdev(values)/math.sqrt(len(values))
    return [mean(values)-delta,mean(values)+delta]


def calibration(values, targets):
    return [{'bin':f'{lo/5:.1f}–{(lo+1)/5:.1f}','n':len(xs),
             'mean_p':mean(p for p,y in xs) if xs else None,
             'frequency':mean(y for p,y in xs) if xs else None}
            for lo in range(5) for xs in [[(p,y) for p,y in zip(values,targets)
                if lo/5<=p<(lo+1)/5 or lo==4 and p==1]]]


def metrics(probabilities, targets, baselines):
    brier=[sum((v-int(i==target))**2 for i,v in enumerate(ps)) for ps,target in zip(probabilities,targets)]
    baseline_brier=[sum((v-int(i==target))**2 for i,v in enumerate(ps)) for ps,target in zip(baselines,targets)]
    loss=[-math.log(max(ps[t],1e-12)) for ps,t in zip(probabilities,targets)]
    baseline_loss=[-math.log(max(ps[t],1e-12)) for ps,t in zip(baselines,targets)]
    return {'n':len(targets),'brier':mean(brier),'log_loss':mean(loss),
            'baseline_brier':mean(baseline_brier),'baseline_log_loss':mean(baseline_loss),
            'brier_mean_interval_95':interval(brier),'log_loss_mean_interval_95':interval(loss),
            'brier_improvement_interval_95':interval([b-a for a,b in zip(brier,baseline_brier)])}


def temporal_evaluation(rows,lines,xi):
    start=int(len(rows)*.8)
    # Keep simultaneous result-availability timestamps together.
    while start>0 and rows[start-1]['date']==rows[start]['date']:start-=1
    if start<45:
        return {'status':'experimental','n':0,'reason':'Muestra temporal insuficiente.'}
    block=max(1,math.ceil((len(rows)-start)/3))
    folds=[];probabilities=[];targets=[];baselines=[];skipped=[];evaluated=[]
    total_data={str(line):{'p':[],'y':[],'baseline':[]} for line in lines}
    cursor=start
    while cursor<len(rows):
        end=min(len(rows),cursor+block)
        while end<len(rows) and rows[end-1]['date']==rows[end]['date']:end+=1
        test=rows[cursor:end];train=[r for r in rows[:cursor] if r['date']<test[0]['date']]
        model=fit(train,test[0]['date'],xi)
        counts=[sum((r['hg']>r['ag'],r['hg']==r['ag'],r['hg']<r['ag'])[i] for r in train) for i in range(3)]
        baseline=[(count+1)/(len(train)+3) for count in counts]
        total_baselines={str(line):(sum(r['hg']+r['ag']>line for r in train)+1)/(len(train)+2) for line in lines}
        folds.append({'train_n':len(train),'train_to':train[-1]['date'],'from':test[0]['date'],'to':test[-1]['date'],
                      'train_ids':[r.get('event_id',r['date']+':'+r['home']+':'+r['away']) for r in train]})
        for row in test:
            identity=row.get('event_id',row['date']+':'+row['home']+':'+row['away'])
            try:grid=model.predict(row['home'],row['away'])
            except (ValueError,KeyError):
                skipped.append(identity);continue
            ps=list(map(float,grid.home_draw_away))
            target=0 if row['hg']>row['ag'] else 1 if row['hg']==row['ag'] else 2
            probabilities.append(ps);targets.append(target);baselines.append(baseline);evaluated.append(identity)
            for line in lines:
                bucket=total_data[str(line)]
                bucket['p'].append(float(grid.total_goals('over',line)))
                bucket['y'].append(int(row['hg']+row['ag']>line));bucket['baseline'].append(total_baselines[str(line)])
        cursor=end
    if not targets:return {'status':'experimental','n':0,'reason':'Sin partidos evaluables.','skipped_ids':skipped}
    totals={key:{**metrics([[p,1-p] for p in bucket['p']],[0 if y else 1 for y in bucket['y']],
                          [[p,1-p] for p in bucket['baseline']]),
                 'calibration':calibration(bucket['p'],bucket['y'])} for key,bucket in total_data.items()}
    per_class={label:calibration([p[i] for p in probabilities],[int(t==i) for t in targets])
               for i,label in enumerate(['home','draw','away'])}
    return {'status':'experimental','protocol':'expanding-window-3-blocks-80-20',
            **metrics(probabilities,targets,baselines),'train_n':folds[0]['train_n'],'train_to':folds[0]['train_to'],
            'from':folds[0]['from'],'to':folds[-1]['to'],'folds':folds,'evaluated_ids':evaluated,'skipped_ids':skipped,
            'calibration':per_class['home'],'calibration_1x2':per_class,'totals':totals,
            'reason':'Evaluación temporal inicial sin omisión deliberada del bloque posterior. Intervalos normales descriptivos; muestra limitada, partidos dependientes y sin validación económica. Baseline: frecuencias suavizadas de cada entrenamiento.'}


def predict(rows, home, away, cutoff, total_lines=None, home_id=None, away_id=None, xi=None):
    xi=settings.model_xi if xi is None else xi
    eligible=sorted([dict(r) for r in rows if r['date']<cutoff],key=lambda r:(r['date'],str(r.get('event_id',''))))
    if home_id is not None or away_id is not None:
        if not home_id or not away_id or any(not r.get('home_id') or not r.get('away_id') or r.get('provider')!='ESPN' for r in eligible):
            return {'status':'unavailable','reason':'Identidad histórica ESPN no verificada.'}
        for row in eligible:
            row['home']='espn:'+str(row['home_id']);row['away']='espn:'+str(row['away_id'])
        home='espn:'+str(home_id);away='espn:'+str(away_id)
    teams={r[side] for r in eligible for side in ['home','away']}
    if len(eligible)<60 or home not in teams or away not in teams or any(sum(t in [r['home'],r['away']] for r in eligible)<5 for t in teams):
        return {'status':'unavailable','reason':'Muestra insuficiente o equipos sin identidad histórica verificada.'}
    lines=sorted(set([x+.5 for x in range(6)]+[float(x) for x in (total_lines or []) if 0<float(x)<20 and float(x)%1==.5]))
    model=fit(eligible,cutoff,xi);grid=model.predict(home,away)
    fingerprint=hashlib.sha256(json.dumps(eligible,sort_keys=True).encode()).hexdigest()
    return {'status':'experimental','model':'penaltyblog/DixonColes-1.13.1','xi':xi,'cutoff':cutoff,
            'sample_n':len(eligible),'sample_from':eligible[0]['date'],'sample_to':eligible[-1]['date'],
            'training_data_sha256':fingerprint,'home_draw_away':list(map(float,grid.home_draw_away)),
            'totals':{str(line):float(grid.total_goals('over',line)) for line in lines},
            'score_distribution':grid.grid.tolist(),'evaluation':temporal_evaluation(eligible,lines,xi)}
