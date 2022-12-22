
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from db.models import dbmodels
from db.dblib import engine

from routers.api_v1.api import api_router
from core.config import settings

from celery import Celery

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
        openapi_url=f"{settings.API_V1_STR}/openapi.json", 
        debug=True)

root_router = APIRouter()

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

@root_router.get("/api/v1", status_code=200)
async def root():
    return {"message": "CardanoPythonLib Api"}

cardanodatos.include_router(root_router)
cardanodatos.include_router(api_router, prefix=settings.API_V1_STR)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(cardanodatos, host="0.0.0.0", port=8001, reload=False, log_level="debug")