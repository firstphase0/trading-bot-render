from .strategy import enhanced_backtest_strategy
def _gen_random_walk(n=500, seed=42):
    import numpy as np
    import pandas as pd
    rng = np.random.default_rng(seed)
    steps = rng.normal(0, 1, n).cumsum()
    price = 100 + steps
    high = price + rng.uniform(0,1,n)
    low = price - rng.uniform(0,1,n)
    openp = np.roll(price,1); openp[0]=price[0]
    vol = rng.integers(100, 200, n)
    return pd.DataFrame({"open":openp,"high":high,"low":low,"close":price,"volume":vol})

def simulate(df, atr_stop_mult=1.5, atr_take_mult=3.0, risk_per_trade=0.01, seed=0):
    out = enhanced_backtest_strategy(df, initial_balance=10000.0, risk_per_trade=risk_per_trade)
    return out['balance']
