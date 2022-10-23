
import json

import dblib
import uvicorn
from cardanopythonlib import base, path_utils
from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from models import *
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

cardanodatos = FastAPI(title=title, description=description, contact=contact, debug=True)

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

@cardanodatos.get("/cardanodatos/status", 
                tags=["Query blockchain"],
                summary="This is the query tip to the blockchain",
                response_description="query tip"
                )
async def check_status():
    """It returns basic info about the status of the blockchain"""
    return node.query_tip_exec()

@cardanodatos.get("/cardanodatos/protocolParams",
                tags=["Query blockchain"],
                summary="Protocol parameters",
                response_description="Protocol parameters"
                )
async def query_protocolParams():
    """It returns the protocol parameters of the blockchain"""
    return node.query_protocol()

@cardanodatos.get("/cardanodatos/address/{command_name}/{address}", 
                tags=["Query blockchain"],
                summary="Query address",
                response_description="Wallet balance/Utxos list"
                )
async def cardano_address(address: str, command_name: NodeCommandName):
    """Get balance or utxo list of specified address or wallet stored \n
    **address**: Address in bech32 format or wallet id stored in local DB. \n
    **command_name**: It can be balance to get overall balance consolidated or utxos to get the list of utxos associated.
    """
    response = None
    if command_name is NodeCommandName.utxos:
        response = node.get_transactions(address)
    elif command_name is NodeCommandName.balance:
        response = node.get_balance(address)

    return(response)

@cardanodatos.post("/cardanodatos/keys/generate", status_code=201, 
                tags=["Keys"],
                summary="Create wallet using mnemonics as root key",
                response_description="Keys generated"
                )
async def create_keys(key: KeyCreate) -> dict:
    """Generate full wallet with mnemonics, cardano keys and base address
        This method does not store any wallet info if the save_flag is False
        If the save_flag is True, cardano cli skeys are stored in local db.\n
        **name**: wallet name if to be stored in local db.\n
        **size**: mnemonic size (12, 15, 24).\n
        **save_flag**: If to be stored in local db. It only stores cardano cli skeys to sign transactions
    """
    if key.name is None:
        key.name = "WalletDummyName"
    key_created = keys.deriveAllKeys(key.name, size = key.size, save_flag = key.save_flag)
    return dblib.insert_wallet(key.name, key_created, key.save_flag)

@cardanodatos.post("/cardanodatos/keys/mnemonics", status_code=201, 
                tags=["Keys"],
                summary="Generate mnemonics only",
                response_description="mnemonics generated"
                )
async def generate_mnemonics(size: int = 24) -> list:
    """It generates the mnemonics only. This method never stores
            any info in local db.\n
        **size**: mnemonic size (12, 15, 24).
    """
    return keys.generate_mnemonic(size)

@cardanodatos.post("/cardanodatos/keys/recover", status_code=201, 
                tags=["Keys"],
                summary="Recover wallet by using mnemonics",
                response_description="Recover keys info"
                )
async def recover_keys(key: KeyRecover) -> dict:
    """Generate full wallet cardano keys and base address from mnemonics\n
    **name**: wallet name if to be stored in local db.\n
    **words**: The mnemonic list\n
    **save_flag**: If to be stored in local db. It only stores cardano cli skeys to sign transactions
    """
    if key.name is None:
        key.name = "WalletDummyName"
    key_created = keys.deriveAllKeys(key.name, words = key.words, save_flag = key.save_flag)
    return dblib.insert_wallet(key.name, key_created, key.save_flag)

@cardanodatos.post("/cardanodatos/transactions/simplesend", status_code=201, 
                tags=["Transactions"],
                summary="Simple send of ADA (not tokens) to multiple addresses",
                response_description="Transaction submit"
                )
async def simple_send(send_params: SimpleSend) -> dict:
    """
    Simple send of ADA (not tokens) to multiple addresses.
    The system needs to have the skeys in local db to sign and submit. 
    Otherwise use the build_tx endpoint.\n
    **wallet_id**: wallet id provided when generated with create_keys endpoint.\n
    **address_destin**: List of addresses in bech32 format to send ADA.\n
    **amount**: Amount in lovelace.\n
    **metadata**: Metadata info if specified.\n
    **witness**: Default 1.\n
    """
    success_flag = False
    fees = 0
    msg = ""
    id = send_params.wallet_id
    (address_origin, payment_vkey) = dblib.get_address_origin('wallet', id)
    address_destin = send_params.address_destin
    address_destin_dict = [item.dict() for item in address_destin]
    params = {
        "address_origin": address_origin,
        "address_destin": address_destin_dict,
        "change_address": address_origin,
        "metadata": send_params.metadata,
        "mint": None,
        "script_path": None,
        "witness": send_params.witness,
    }

    sign_response = None
    submit_response = None

    build_response = node.build_tx_components(params)
    tx_id = node.get_txid_body()

    if build_response is not None:
        fees = build_response.split(' ')[-1][:-1]
        sign_file_name = 'temp_' + id
        sign_path = node.KEYS_FILE_PATH + '/'
        sign_file_name = 'temp_' + id
        path_utils.save_file(sign_path + sign_file_name + '/', sign_file_name + '.payment.skey', payment_vkey)
        sign_response = node.sign_transaction(sign_file_name)
        if sign_response is not None:
            success_flag = True
            tx_id = node.get_txid_signed()[:-1]
            tx_analysis = json.dumps(node.analyze_tx_signed())
            submit_response = node.submit_transaction()[:-1]
            msg = "Transaction signed and submit"
            path_utils.remove_folder(sign_path + sign_file_name)
            cbor_tx_path = base.Starter(config_path).TRANSACTION_PATH_FILE + '/tx.signed'
            with open(cbor_tx_path, 'r') as file:
                cbor_tx_file = json.load(file)
        else:
            msg = "Problems signing the transaction"
            cbor_tx_file = {"msg": msg}
    else:
        msg = "Problems building the transaction"
        cbor_tx_file = {"msg": msg}
    
    # Check if transaction is already stored in db
    tableName = 'transactions'
    query = f"SELECT * FROM {tableName} WHERE id = '{tx_id}';"
    ids = dblib.read_query(query)
    tx_info = {
        "msg": msg,
        "success_flag": success_flag,
        "wallet_origin_id": id,
        "tx_id": tx_id,
        "tx_details": params,
        "fees": fees,
        "sign": sign_response,
        "submit": submit_response,
        "tx_cborhex": cbor_tx_file
    }

    if ids != []:
        tx_info["msg"] = "Transaction id already exists in database"
    else:
        id = dblib.insert_transaction(tx_info, config_path=config_path)

    return tx_info

@cardanodatos.post("/cardanodatos/transactions/buildtx", status_code=201, 
                tags=["Transactions"],
                summary="Simple build of tx to send ADA (not tokens) to multiple addresses",
                response_description="Build tx"
                )
async def build_tx(build_tx: BuildTx) -> dict:
    """
    Build_tx only builds the transaction, not sign or submit. 
    Simple send of ADA (not tokens) to multiple addresses.
    The main output is the tx file in cbor format.\n

    **address_origin**: address from where to send the ADA in bech32 format.\n
    **address_destin**: List of addresses in bech32 format to send ADA.\n
    **amount**: Amount in lovelace.\n
    **metadata**: Metadata info if specified.\n
    **witness**: Default 1.\n
    """
    success_flag = False
    fees = 0
    msg = ""

    address_origin = build_tx.address_origin
    address_destin = build_tx.address_destin
    address_destin_dict = [item.dict() for item in address_destin]
    params = {
        "address_origin": address_origin,
        "address_destin": address_destin_dict,
        "change_address": address_origin,
        "metadata": build_tx.metadata,
        "mint": None,
        "script_path": None,
        "witness": build_tx.witness,
    }
    build_response = node.build_tx_components(params)
    tx_id = node.get_txid_body()

    if build_response is not None:
        fees = build_response.split(' ')[-1][:-1]
        success_flag = True
        msg = "Transaction build succesfull"
        tx_id = node.get_txid_body()[:-1]
        cbor_tx_path = base.Starter(config_path).TRANSACTION_PATH_FILE + '/tx.draft'
        with open(cbor_tx_path, 'r') as file:
            cbor_tx_file = json.load(file)
    else:
        msg = "Problems building the transaction"
        cbor_tx_file = {"msg": msg}
    
    # Check if transaction is already stored in db
    tableName = 'transactions'
    query = f"SELECT * FROM {tableName} WHERE id = '{tx_id}';"
    ids = dblib.read_query(query)
    tx_info = {
        "msg": msg,
        "success_flag": success_flag,
        "tx_id": tx_id,
        "tx_details": params,
        "fees": fees,
        "tx_cborhex": cbor_tx_file
    }
    return tx_info

@cardanodatos.post("/cardanodatos/transactions/submit", status_code=201, 
                tags=["Transactions"],
                summary="Submit the transaction",
                response_description="Tx submit"
                )
async def submit_tx(file: UploadFile):
    """The only purpose of this endpoint is to submit a tx file already signed.\n
    **file**: the file needs to be uploaded after signed.\n
    """

    tx_signed = await file.read()
    tx_signed = str(tx_signed, 'utf-8')
    sign_file_name = 'tx.signed'
    sign_path = node.TRANSACTION_PATH_FILE + '/'
    path_utils.save_file(sign_path, sign_file_name, tx_signed)
    submit_response = node.submit_transaction()[:-1]
    if "Command failed" in submit_response:
        msg = "Problems while building the transaction"
    else:
        msg = "Transaction succesfully submitted"
    tx_info = {
        "msg": msg,
        "success_flag": True,
        "submit": submit_response
    }
    return tx_info

@cardanodatos.post("/cardanodatos/transactions/mint", status_code=201, 
                tags=["Transactions"],
                summary="Mint tokens under specified policyID",
                response_description="Mint confirmation"
                )
async def mint(mint_params: Mint) -> dict:
    """Mint tokens under specified policyID.
    The script must exists in local db. To create a mint script use the mint script endpoint\n
    **script_id**: id of the file stored in local db.\n
    **tokens**: list of tokens to mint with:\n
    **name**: name of the token\n
    **amount**: quantity of tokens to be minted\n
    """
    success_flag = False
    fees = 0
    sign_response = None
    submit_response = None
    msg = ""
    id = mint_params.wallet_id
    mint = None
    (address_origin, payment_vkey) = dblib.get_address_origin('wallet', id)
    sign_file_name = 'temp_' + id
    sign_path = node.KEYS_FILE_PATH + '/'
    sign_file_name = 'temp_' + id
    path_utils.save_file(sign_path + sign_file_name + '/', sign_file_name + '.payment.skey', payment_vkey)
    address_destin = mint_params.address_destin
    address_destin_dict = [item.dict() for item in address_destin]

    script_id = mint_params.script_id
    tokens = [item.dict() for item in mint_params.tokens]

    # Check if script exists in db
    tableName = 'scripts'
    query = f"SELECT * FROM {tableName} WHERE id = '{script_id}';"
    script_db = dblib.read_query(query)

    if script_db != []:
        purpose = script_db[0][2]
        if purpose == 'mint':
            simple_script = script_db[0][3]
            policyID = script_db[0][4]

            # Extract the time rule from the script if any
            script_field = simple_script.get("scripts", None)
            validity_interval = None
            # Asuming a simple script with just one item inside the script field
            if script_field is not None:
                for fields in script_field:
                    for k, v in fields.items():
                        print("#####################################",k, v)
                        if v in ["before", "after"]:
                            print("#############################################")
                            type_time = v
                            slot = fields["slot"]
                            validity_interval = {"slot": slot, "type": type_time}
                        else:
                            msg = "Check validity interval fields"
                            mint = None
            
                # Create the script file
                script_name = script_db[0][1] + '.script'
                script_file_path = node.MINT_FOLDER
                path_utils.save_metadata(script_file_path, script_name, simple_script)
                script_file_path = node.MINT_FOLDER + '/' + script_name

                # Build the mint field
                mint = {
                    "policyID": policyID,
                    "policy_path": script_file_path,
                    "validity_interval": validity_interval,
                    "tokens": tokens
                }
            else:
                msg = "Could not find script for minting"
            
        else:
            msg = "Script purpose is not for minting"
    else:
        msg = "Could not find script for minting"


    params = {
        "address_origin": address_origin,
        "address_destin": address_destin_dict,
        "change_address": address_origin,
        "metadata": mint_params.metadata,
        "mint": mint,
        "script_path": None,
        "witness": mint_params.witness,
    }
    build_response = node.build_tx_components(params)
    print("hola", build_response)
    tx_id = node.get_txid_body()

    if build_response is not None:
        success_flag = True
        fees = build_response.split(' ')[-1][:-1]
        sign_response = node.sign_transaction(sign_file_name)
        if sign_response is not None:
            tx_id = node.get_txid_signed()[:-1]
            tx_analysis = json.dumps(node.analyze_tx_signed())
            # submit_response = node.submit_transaction()
            msg = "Transaction signed and submit"
        else:
            msg = "Problems signing the transaction"
    else:
        msg = "Problems building the transaction"
    # Remove temp files
    path_utils.remove_folder(sign_path + sign_file_name)

    # Check if transaction is already stored in db
    tableName = 'transactions'
    query = f"SELECT * FROM {tableName} WHERE id = '{tx_id}';"
    ids = dblib.read_query(query)
    tx_info = {
        "msg": msg,
        "success_flag": success_flag,
        "wallet_origin_id": id,
        "tx_id": tx_id,
        "tx_details": params,
        "fees": fees,
        "sign": sign_response,
        "submit": submit_response
    }
    if ids != []:
        tx_info["msg"] = "Transaction id already exists in database"
    else:
        id = dblib.insert_transaction(tx_info, config_path=config_path)

    return tx_info

@cardanodatos.post("/cardanodatos/uploadScript/{script_purpose}", status_code=201, 
                tags=["Scripts"],
                summary="Upload an existing script file",
                response_description="Script uploaded"
                )
async def upload_script(script_name: str, file: UploadFile, script_purpose: ScriptPurpose):
    """Upload script file and stores it in local db. Purpose: mint, multisig\n
    **file**: script file to be uploaded.\n
    """
    id = None
    script_content = await file.read()
    # script_content = str(script_content, 'utf-8')
    script_file_path = node.MINT_FOLDER
    script_content = json.loads(script_content)
    path_utils.save_metadata(script_file_path, script_name, script_content)
    policyID = node.create_policy_id(script_purpose, script_name)
    if policyID is not None:
        id = dblib.insert_script(script_name, script_purpose, script_content, policyID)
    
    response = {
        "msg": "Script created in local DB",
        "script_id": id,
        "policyID": policyID,
    }
    return response

# @cardanodatos.get("/cardanodatos/queryScript")
# async def query_script():
        
#     tableName = 'scripts'
#     query = f"SELECT * FROM {tableName};"
#     scripts = dblib.read_query(query)
#     return scripts

@cardanodatos.post("/cardanodatos/simplescript/{script_purpose}", status_code=201, 
                tags=["Scripts"],
                summary="",
                response_description="Script creation"
                )
async def simpleScript(simpleScript_params: Script, script_purpose: ScriptPurpose) -> dict:
    """Creation of a script depending of its purpose: mint or multisig.\n
    **name**: name of the script.\n
    **type**: type of the script. Options are: all, any, atLeast.\n
    **required**: if script type is atLeast, number of required signers must be provided.\n
    **hashes**: list of pubKeyHashes.\n
    **type_time**: if script constraint by time. Options are: before, after.\n
    **slot**: slot for the validity range.
    """
    name = simpleScript_params.name
    parameters = {
        "name": name,
        "type": simpleScript_params.type,
        "required": simpleScript_params.required,
        "hashes": simpleScript_params.hashes,
        "type_time": simpleScript_params.type_time,
        "slot": simpleScript_params.slot,
        "purpose": script_purpose
    }
    # simple_script, policyID = node.create_simple_script(name, script_purpose, type, required, hashes)
    simple_script, policyID = node.create_simple_script(parameters=parameters)
    if simple_script is None or policyID is None:
        response = {"msg": "Problems building the script"}
    else:
        script_purpose = script_purpose._value_
        id = dblib.insert_script(name, script_purpose, simple_script, policyID)
        response = {
            "msg": "Script created",
            "script_id": id,
            "policyID": policyID,
            "content": simple_script
        }
    
    if script_purpose == 'mint':
        script_file_path = node.MINT_FOLDER
    elif script_purpose == 'multisig':
        script_file_path = node.MULTISIG_FOLDER

    script_file_name = '/' + name + '.script'
    policy_file_name = '/' + name + '.policyid'
    path_utils.remove_file(script_file_path, script_file_name) # type:ignore
    path_utils.remove_file(script_file_path, policy_file_name) # type:ignore
    return response

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