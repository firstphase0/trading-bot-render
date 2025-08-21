from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from .models import ModelVersion, ConfigKV
from .config import StrategyConfig

def get_current_config(db: Session) -> StrategyConfig:
    row = db.query(ConfigKV).filter(ConfigKV.key == "strategy_config").first()
    if row is None:
        cfg = StrategyConfig().dict()
        row = ConfigKV(key="strategy_config", value=cfg)
        db.add(row)
        db.commit()
        db.refresh(row)
    return StrategyConfig(**row.value)

def save_config(db: Session, cfg: StrategyConfig):
    row = db.query(ConfigKV).filter(ConfigKV.key == "strategy_config").first()
    if row is None:
        row = ConfigKV(key="strategy_config", value=cfg.dict())
        db.add(row)
    else:
        row.value = cfg.dict()
    db.commit()

def get_best_model(db: Session):
    return db.query(ModelVersion).filter(ModelVersion.promoted==True).order_by(ModelVersion.id.desc()).first()

def save_candidate(db: Session, version: str, metrics: Dict[str, Any], promote: bool=False):
    mv = ModelVersion(version=version, metrics=metrics, promoted=promote)
    db.add(mv)
    db.commit()
    db.refresh(mv)
    return mv
