from sqlalchemy.orm import Session
from .repository import get_best_model
def healthcheck(db: Session) -> dict:
    best = get_best_model(db)
    return {"status":"ok", "best_model": best.version if best else None}
