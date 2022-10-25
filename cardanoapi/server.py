
import json

import uvicorn
from cardanopythonlib import base
from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from routers import blockchain_api, keys_api, transactions_api, scripts_api
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




##############################################################################################

# S3_BUKECT_NAME = "moxievideos"

# class VideoModel(BaseModel):
#     id: int
#     video_title: str
#     video_url: str

# @cardanodatos.get("/videos", response_model=List[VideoModel])
# async def get_videos():
#     # Connect to our database
#     conn = psycopg2.connect(
#         host="0.0.0.0", database="cardanodatos", user="cardanodatos", password="cardanodatos", port=5435
#     )
#     cur = conn.cursor()
#     cur.execute("SELECT * FROM videos ORDER BY id DESC")
#     rows = cur.fetchall()

#     formatted_videos = []
#     for row in rows:
#         formatted_videos.append(
#             VideoModel(id=row[0], video_title=row[1], video_url=row[2])
#         )
    
#     cur.close()
#     conn.close()
#     return formatted_videos

# @cardanodatos.post("/videos", status_code=201)
# async def add_video(file: UploadFile):
#     # Upload the file to AWS S3
#     s3 = boto3.resource("s3")
#     bucket = s3.Bucket(S3_BUKECT_NAME)  # type: ignore
#     bucket.upload_fileobj(file.file, file.filename, ExtraArgs={"ACL": "public-read"})

#     uploaded_file_url = f"https://{S3_BUKECT_NAME}.s3.amazonaws.com/{file.filename}"

#     # Connect to our database
#     conn = psycopg2.connect(
#         host="0.0.0.0", database="cardanodatos", user="cardanodatos", password="cardanodatos", port=5435
#     )
#     cur = conn.cursor()
#     cur.execute(f"INSERT INTO videos (video_title, video_url) VALUES ('{file.filename}', '{uploaded_file_url}')")
#     print("current execution")
#     conn.commit()
    
#     cur.close()
#     conn.close()
if __name__ == "__main__":

    # s3 = boto3.client('s3')
    # response = s3.list_buckets()
    # print('Existing buckets:')
    # for bucket in response['Buckets']:
    #     print(f'  {bucket["Name"]}')
    uvicorn.run(cardanodatos, host="0.0.0.0", port=8000, reload=False)

    # response = keys.deriveAllKeys('test', size = 24)
    # id = dblib.insert_wallet(response)
    # print(id)