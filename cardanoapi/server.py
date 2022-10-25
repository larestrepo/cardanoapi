
import uvicorn
from cardanopythonlib import base
from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from routers import blockchain_api, keys_api, transactions_api, scripts_api, admin_api
from db.models import dbmodels
from db.dblib import engine

from celery import Celery

config_path = './config.ini' # Optional argument
starter = base.Starter(config_path)
node = base.Node(config_path) # Or with the default ini: node = base.Node()
keys = base.Keys(config_path)

database_flag = 'postgresql' # Other option could be dynamodb

description = "This is the main gate to interact with the CardanoPython Lib"
title = "CardanoPython Lib API"
version = "0.0.1"
contact = {
    "name": "Moxie",
    "TickerPool": "MoxiePool"
}

dbmodels.Base.metadata.create_all(bind=engine)

cardanodatos = FastAPI(
        title=title, 
        description=description, 
        contact=contact, 
        debug=True)

cardanodatos.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

celery = Celery(
    __name__,
    broker="redis://127.0.0.1:6379/0",
    backend="redis://127.0.0.1:6379/0"
)

#Simulate long task
@celery.task
def divide(x, y):
    import time
    time.sleep(5)
    return x / y

##################################################################
# Start of the endpoints
##################################################################

cardanodatos.include_router(blockchain_api.router)
cardanodatos.include_router(keys_api.router)
cardanodatos.include_router(transactions_api.router)
cardanodatos.include_router(scripts_api.router)
cardanodatos.include_router(admin_api.router)


if __name__ == "__main__":

    uvicorn.run(cardanodatos, host="0.0.0.0", port=8000, reload=False)