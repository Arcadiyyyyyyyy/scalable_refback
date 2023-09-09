import logging
from sys import stderr

from fastapi import FastAPI

from src.router import router as calculation_router


# Configure logging
logging.getLogger('apscheduler').setLevel(logging.WARNING)

logger = logging.getLogger()

try:
    logger.removeHandler(logger.handlers[0])
except IndexError:
    pass

logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(filename)s | Line: %(lineno)d | %(name)s | %(message)s')

stdout_handler = logging.StreamHandler(stderr)
stdout_handler.setLevel(logging.DEBUG)
stdout_handler.setFormatter(formatter)

file_handler = logging.FileHandler('logs.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(stdout_handler)


# Configure FastAPI
app = FastAPI(title="Random generator")

app.include_router(calculation_router)
