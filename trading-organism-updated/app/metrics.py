import numpy as np
import pandas as pd

def compute_metrics(equity: pd.Series, periods_per_year: int = 252) -> dict:
    r = equity.pct_change().dropna()
    if r.empty:
        return {"cagr":0, "sharpe":0, "sortino":0, "max_drawdown":0, "winrate":0}
    avg = r.mean()*periods_per_year
    vol = r.std()*np.sqrt(periods_per_year)
    sharpe = avg/(vol+1e-9)
    neg = r[r<0]
    dvol = neg.std()*np.sqrt(periods_per_year) if not neg.empty else 0
    sortino = avg/(dvol+1e-9)
    roll_max = equity.cummax()
    dd = (equity/roll_max - 1).min()
    wins = (r>0).sum(); total = r.count()
    winrate = wins/total if total>0 else 0
    years = len(equity)/periods_per_year
    cagr = (equity.iloc[-1]/equity.iloc[0])**(1/max(years,1e-9)) - 1
    return {"cagr":float(cagr), "sharpe":float(sharpe), "sortino":float(sortino), "max_drawdown":float(dd), "winrate":float(winrate)}
