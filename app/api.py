from fastapi import FastAPI, Depends
from .db import Base, engine, get_db
from sqlalchemy.orm import Session
from .repository import get_current_config, save_config, get_best_model, save_candidate
from .health import healthcheck
from .notify import notify
from .logging_conf import setup_logging
from .config import StrategyConfig
setup_logging()
Base.metadata.create_all(bind=engine)
app = FastAPI(title="Trading Organism API")
CURRENT_VERSION = "none"

@app.get("/")
def root(db: Session = Depends(get_db)):
    cfg = get_current_config(db)
    best = get_best_model(db)
    return {"message":"Bot is alive!", "serving_version": CURRENT_VERSION, "best_version": best.version if best else None, "config": cfg.dict()}

@app.get("/health")
def health(db: Session = Depends(get_db)):
    return healthcheck(db)

@app.get("/metrics")
def metrics(db: Session = Depends(get_db)):
    best = get_best_model(db)
    return best.metrics if best else {"note":"no model yet"}

@app.post("/reload")
def reload_model(version: str, db: Session = Depends(get_db)):
    global CURRENT_VERSION
    CURRENT_VERSION = version
    notify(f"Reloaded to {version}")
    return {"status":"ok","serving_version":CURRENT_VERSION}

@app.post("/config")
def update_config(cfg: dict, db: Session = Depends(get_db)):
    sc = StrategyConfig(**cfg)
    save_config(db, sc)
    return {"status":"ok","config":sc.dict()}

@app.get("/best_model")
def best_model(db: Session = Depends(get_db)):
    bm = get_best_model(db)
    return {"version": bm.version, "metrics": bm.metrics} if bm else {}
