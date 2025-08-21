import numpy as np
from typing import Dict
from .metrics import compute_metrics
from .backtest import _gen_random_walk, simulate

def evaluate_candidate(params: Dict, seed:int=0) -> Dict:
    df = _gen_random_walk(n=800, seed=seed)
    eq = simulate(df,
                  atr_stop_mult=params.get('atr_stop_mult',1.5),
                  atr_take_mult=params.get('atr_take_mult',3.0),
                  risk_per_trade=params.get('risk_per_trade',0.01),
                  seed=seed)
    m = compute_metrics(eq, periods_per_year=252)
    m['len']=int(len(eq))
    return m

def mutate(params: Dict, scale: float=0.2, rng=None):
    if rng is None:
        rng = np.random.default_rng()
    p=params.copy()
    for k in ['atr_stop_mult','atr_take_mult','risk_per_trade']:
        val = p.get(k, 1.0)
        noise = 1 + rng.normal(0, scale)
        if k=='risk_per_trade':
            p[k]=max(0.001, min(0.05, val*noise))
        else:
            p[k]=max(0.5, min(6.0, val*noise))
    return p

def breed(parent_a: Dict, parent_b: Dict, rng=None):
    if rng is None:
        rng = np.random.default_rng()
    child={}
    for k in set(list(parent_a.keys())+list(parent_b.keys())):
        child[k] = parent_a.get(k,1.0) if rng.random()<0.5 else parent_b.get(k,1.0)
    return child
