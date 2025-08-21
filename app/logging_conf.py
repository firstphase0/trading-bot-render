import logging, os, sys
def setup_logging(level=os.getenv("LOG_LEVEL", "INFO")):
    logger = logging.getLogger()
    if logger.handlers:
        return
    logger.setLevel(level)
    h = logging.StreamHandler(sys.stdout)
    fmt = logging.Formatter('%(asctime)s %(levelname)s %(name)s - %(message)s')
    h.setFormatter(fmt)
    logger.addHandler(h)
