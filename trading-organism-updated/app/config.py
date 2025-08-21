import os
from pydantic import BaseModel

class StrategyConfig(BaseModel):
    ema_fast:int = 21
    ema_slow:int = 50
    rsi_low:int = 30
    rsi_high:int = 70
    atr_stop_mult:float = 1.5
    atr_take_mult:float = 3.0
    risk_per_trade:float = 0.01
    confidence_threshold:float = 0.5

def env(key:str, default:str=""):
    return os.getenv(key, default)

API_PORT = int(env("API_PORT", "8000"))
API_BASE_URL = env("API_BASE_URL", f"http://localhost:{API_PORT}")
API_RELOAD_ENDPOINT = env("API_RELOAD_ENDPOINT", "/reload")
PROMOTE_DELTA = float(env("PROMOTE_DELTA", "0.02"))
MAX_DRAWDOWN_LIMIT = float(env("MAX_DRAWDOWN_LIMIT", "-0.35"))
EVOLVE_INTERVAL = int(env("EVOLVE_INTERVAL", "60"))
POPULATION = int(env("POPULATION", "6"))
GENERATIONS = int(env("GENERATIONS", "2"))
WEBHOOK_URL = env("WEBHOOK_URL", "")
