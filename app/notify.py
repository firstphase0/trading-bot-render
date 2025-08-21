import os, requests
def notify(text:str, extra:dict=None):
    url = os.getenv("WEBHOOK_URL", "")
    if not url:
        return
    payload = {"text": text, "extra": extra or {}}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception:
        pass
