import logging
import os

from logging.handlers import RotatingFileHandler

def initLog(sFileLog):
    logFormatter = logging.Formatter("%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d]; %(message)s")

    objLog = logging.getLogger()
    objLog.setLevel(logging.DEBUG)
    
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("telethon").setLevel(logging.WARNING)
    logging.getLogger("asyncqt").setLevel(logging.WARNING)
    logging.getLogger("selenium").setLevel(logging.WARNING)

    bRoll = os.path.isfile(sFileLog)

    handler = RotatingFileHandler(sFileLog, backupCount=2)
    handler.setFormatter(logFormatter)

    objLog.addHandler(handler)

    if bRoll:
        objLog.handlers[0].doRollover()
