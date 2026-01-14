import logging 

logger = logging.getLogger("Backend_logger")
logger.setLevel(logging.INFO)

handler =logging.StreamHandler()

formatter = logging.Formatter(
     "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

handler.setFormatter(formatter)

if not logger.handlers:
    logger.addHandler(handler)