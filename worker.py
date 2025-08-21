import os, time, logging, traceback
from sqlalchemy.orm import Session
from app.db import SessionLocal, Base, engine
from app.repository import get_current_config, get_best_model, save_candidate
from app.evolution import evaluate_candidate, mutate, breed
from app.config import PROMOTE_DELTA, MAX_DRAWDOWN_LIMIT, EVOLVE_INTERVAL, POPULATION, GENERATIONS
from app.notify import notify
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
Base.metadata.create_all(bind=engine)
API_BASE = os.getenv("API_BASE_URL", f"http://localhost:{os.getenv('API_PORT','8000')}")
API_RELOAD = os.getenv("API_RELOAD_ENDPOINT", "/reload")

def post_reload(version: str):
    import requests
    try:
        r = requests.post(API_BASE+API_RELOAD, params={"version": version}, timeout=10)
        r.raise_for_status()
    except Exception as e:
        logging.warning("Failed to notify API reload: %s", e)

def evolve_once(db: Session, generation:int=0):
    cfg = get_current_config(db)
    parent = {'atr_stop_mult': cfg.atr_stop_mult, 'atr_take_mult': cfg.atr_take_mult, 'risk_per_trade': cfg.risk_per_trade}
    population=[parent]
    for _ in range(max(1, POPULATION-1)):
        population.append(mutate(parent, scale=0.25))
    scored=[]
    for i,params in enumerate(population):
        m = evaluate_candidate(params, seed=42+generation*100+i)
        scored.append((params,m))
    scored.sort(key=lambda x: (x[1]['sharpe'], -abs(x[1]['max_drawdown'])))
    best_params, best_metrics = scored[-1]
    runner_params, runner_metrics = scored[-2] if len(scored)>1 else (best_params, best_metrics)
    child = breed(best_params, runner_params)
    child = mutate(child, scale=0.15)
    child_metrics = evaluate_candidate(child, seed=84+generation)
    cand_params, cand_metrics = (child, child_metrics) if child_metrics['sharpe']>best_metrics['sharpe'] else (best_params, best_metrics)
    return cand_params, cand_metrics

def main_loop():
    backoff=5
    while True:
        try:
            db = SessionLocal()
            best = get_best_model(db)
            baseline_sharpe = best.metrics['sharpe'] if best else 0.0
            logging.info("Baseline sharpe: %.4f", baseline_sharpe)
            champion_params=None
            champion_metrics=None
            for g in range(GENERATIONS):
                p, m = evolve_once(db, generation=g)
                logging.info("Gen %d candidate: params=%s metrics=%s", g, p, m)
                if champion_metrics is None or m['sharpe']>champion_metrics['sharpe']:
                    champion_params, champion_metrics = p, m
            improved = (champion_metrics['sharpe'] - baseline_sharpe)/(abs(baseline_sharpe)+1e-9)
            logging.info("Improvement: %.2f%%", improved*100)
            if champion_metrics['max_drawdown'] < MAX_DRAWDOWN_LIMIT:
                logging.warning("Rejected: drawdown %.2f below limit %.2f", champion_metrics['max_drawdown'], MAX_DRAWDOWN_LIMIT)
            elif improved > PROMOTE_DELTA:
                version = f"v{int(time.time())}"
                rec = save_candidate(db, version, {"params":champion_params, **champion_metrics}, promote=True)
                notify(f"Promoted {version}", rec.metrics)
                post_reload(version)
            else:
                version = f"c{int(time.time())}"
                save_candidate(db, version, {"params":champion_params, **champion_metrics}, promote=False)
                logging.info("Not promoted (%.2f%% < %.2f%%)", improved*100, PROMOTE_DELTA*100)
            db.close()
            backoff=5
        except Exception:
            logging.error("Worker error:\n%s", traceback.format_exc())
            notify("Worker error", {})
            backoff=min(300, backoff*2)
        time.sleep(EVOLVE_INTERVAL if backoff==5 else backoff)

if __name__ == "__main__":
    main_loop()
