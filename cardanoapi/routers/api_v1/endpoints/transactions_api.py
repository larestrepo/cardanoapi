import json

from fastapi import APIRouter, UploadFile, Depends, HTTPException, Form, File
from sqlalchemy.orm import Session
from db.dblib import get_db
from typing import Optional

from cardanopythonlib import base, path_utils
from routers.api_v1.endpoints.pydantic_schemas import SimpleSend, BuildTx, Mint, SignCommandName, SimpleSign
from db.models import dbmodels

router = APIRouter()

config_path = './config.ini' # Optional argument
# config_path = './cardanoapi/config.ini' # Optional argument
starter = base.Starter(config_path)
node = base.Node(config_path) # Or with the default ini: node = base.Node()



@router.post("/simplesend", status_code=201, 
                summary="Simple send of ADA (not tokens) to multiple addresses",
                response_description="Transaction submit"
                )
async def simple_send(send_params: SimpleSend, db: Session = Depends(get_db)) -> dict:
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

    db_wallet = db.query(dbmodels.Wallet).filter(dbmodels.Wallet.id == id).first()
    if db_wallet is None:
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    address_origin = db_wallet.payment_addr
    payment_skey = db_wallet.payment_skey

    # (address_origin, payment_vkey) = dblib.get_address_origin('wallet', id)
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
        path_utils.save_file(sign_path + sign_file_name + '/', sign_file_name + '.payment.skey', payment_skey)
        sign_response = node.sign_transaction([sign_file_name])
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
            raise HTTPException(status_code=404, detail="Problems signing the transaction")
    else:
        raise HTTPException(status_code=404, detail="Problems building the transaction")
    
    # Check if transaction signed is already stored in db
    db_transaction = db.query(dbmodels.Transactions).filter(dbmodels.Transactions.tx_id == tx_id).first()
    if db_transaction is None:
        db_transaction = dbmodels.Transactions(
            id_wallet = id,
            address_origin = params["address_origin"],
            address_destin = str(params["address_destin"]),
            tx_cborhex = cbor_tx_file,
            metadata = params["metadata"],
            fees = fees,
            network = base.Starter(config_path).CARDANO_NETWORK,
            processed = success_flag,
            tx_id = tx_id
        )
        db.add(db_transaction)
        db.commit()
        db.refresh(db_transaction)
    else:
        raise HTTPException(status_code=404, detail="Transaction id already exists in database")
    return db_transaction

@router.post("/buildtx", status_code=201, 
                summary="Simple build of tx to send ADA (not tokens) to multiple addresses",
                response_description="Build tx"
                )
async def build_tx(build_tx: BuildTx, db: Session = Depends(get_db)) -> dict:
    """
    Build_tx only builds the transaction, not sign or submit. 
    Simple send of ADA (not tokens) to multiple addresses.
    The main output is the tx file in cbor format.\n

    **address_origin**: address from where to send the ADA in bech32 format.\n
    **address_destin**: List of addresses in bech32 format to send ADA.\n
    **amount**: Amount in lovelace.\n
    **metadata**: Metadata info if specified. If not metadata use {}\n
    **mint**: List of tokens to be minted under the specified policy script. if not mint use []\n
    **name**: token name to be minted.\n
    **amount**: amount to be minted.\n
    **script_id**: script id as response returned with the post scripts endpoint. See scripts section. If not script use ""\n
    **witness**: Default 1.\n
    """
    success_flag = False
    fees = 0
    msg = ""

    address_origin = build_tx.address_origin
    address_destin = build_tx.address_destin
    address_destin_dict = [item.dict() for item in address_destin]

    script_id = build_tx.script_id
    mint_dict = None
    script_path = None
    mint = build_tx.mint
    if (script_id == "" and mint != []) or (script_id != "" and mint == []):
        raise HTTPException(status_code=404, detail=f"Script field empty or mint info empty")
    elif script_id != "" and mint != []:
        db_script = db.query(dbmodels.Scripts).filter(dbmodels.Scripts.id == script_id).first()
        if db_script is None or mint is None:
            raise HTTPException(status_code=404, detail=f"Script with id: {script_id} not found or mint field empty")
        else:
            script_name = db_script.name
            script_content = db_script.content
            script_policyID = db_script.policyID
            script_purpose = db_script.purpose
            # Store the script locally to build the tx
            script_file_path = ''
            if script_purpose == 'mint':
                script_file_path = node.MINT_FOLDER
            elif script_purpose == 'multisig':
                script_file_path = node.MULTISIG_FOLDER
            path_utils.save_metadata( script_file_path, script_name + ".script", script_content)
            policyID = node.create_policy_id(script_purpose, script_name)
            script_path = script_file_path + "/" + script_name + ".script"
            # Check script integrity
            if policyID != script_policyID:
                raise HTTPException(status_code=404, detail=f"Script integrity not validated. PolicyID in local db is: {script_policyID} and newly generated policyID is: {policyID}")
            
            mint_list = [item.dict() for item in mint]
            validity_interval = None
            for item in script_content["scripts"]:
                if item["type"] != "sig":
                    validity_interval = {
                        "type": item["type"],
                        "slot": item["slot"]
                    }
            mint_dict = {
                "policyID": policyID,
                "policy_path": script_path,
                "validity_interval": validity_interval,
                "tokens": mint_list
            }

    params = {
        "address_origin": address_origin,
        "address_destin": address_destin_dict,
        "change_address": address_origin,
        "metadata": build_tx.metadata,
        "mint": mint_dict,
        "script_path": script_path,
        "witness": build_tx.witness,
    }
    build_response = node.build_tx_components(params)
    tx_id = node.get_txid_body()

    if build_response is not None:
        fees = build_response.split(' ')[-1][:-1]
        success_flag = True
        msg = "Transaction build succesfull"
        tx_id = node.get_txid_body()[:-1]
        cbor_tx_path = node.TRANSACTION_PATH_FILE + '/tx.draft'
        with open(cbor_tx_path, 'r') as file:
            cbor_tx_file = json.load(file)
    else:
        msg = "Problems building the transaction"
        cbor_tx_file = {"msg": msg}

    tx_info = {
        "msg": msg,
        "success_flag": success_flag,
        "tx_id": tx_id,
        "tx_details": params,
        "fees": fees,
        "tx_cborhex": cbor_tx_file
    }
    return tx_info

@router.post("/signfile", status_code=201, 
                summary="Sign a transaction file",
                response_description="Transaction signed"
                )

async def sign_tx_file(signatures: list[str],
                file: UploadFile= File(...),
                db: Session = Depends(get_db)) -> dict:
    """Sign the draft transaction file with the number of signatures specified. 
     The wallets must exist in the local DB"""
    tx_draft = await file.read()
    tx_draft = str(tx_draft, 'utf-8')
    draft_file_name = 'tx.draft'
    draft_path = node.TRANSACTION_PATH_FILE + '/'
    path_utils.save_file(draft_path, draft_file_name, tx_draft)
    sign_file_name_array = []
    for id in signatures:
        db_wallet = db.query(dbmodels.Wallet).filter(dbmodels.Wallet.id == id).first()
        if db_wallet is None:
            raise HTTPException(status_code=404, detail="Wallet not found")
        payment_skey = db_wallet.payment_skey
        sign_file_name = 'temp_' + str(id)
        sign_path = node.KEYS_FILE_PATH + '/'
        path_utils.save_metadata(sign_path + sign_file_name + '/', sign_file_name + '.payment.skey', payment_skey)
        sign_file_name_array.append(sign_file_name)
    
    cbor_tx_file = {}
    sign_response = node.sign_transaction(sign_file_name_array)

    path_utils.remove_file(draft_path, draft_file_name)
    if sign_response is not None:
        success_flag = True
        tx_id = node.get_txid_signed()[:-1]
        tx_analysis = json.dumps(node.analyze_tx_signed())
        msg = "Transaction signed"
        for id in signatures:
            sign_file_name = 'temp_' + str(id)
            sign_path = node.KEYS_FILE_PATH + '/'
            path_utils.remove_folder(sign_path + sign_file_name)
        cbor_tx_path = draft_path
        with open(cbor_tx_path + 'tx.signed', 'r') as f:
            cbor_tx_file = json.load(f)
        path_utils.remove_file(cbor_tx_path, 'tx.signed')
    else:
        raise HTTPException(status_code=404, detail="Problems signing the transaction")

    tx_info = {
        "msg": msg,
        "success_flag": success_flag,
        "tx_id": tx_id,
        "tx_cborhex": cbor_tx_file

    }
    return tx_info

@router.post("/sign", status_code=201, 
                summary="Sign the transaction",
                response_description="Transaction signed"
                )

async def sign_tx(signatures: list[str],
                tx_cborhex: dict,
                db: Session = Depends(get_db)) -> dict:
    """Sign the draft transaction sent in json format with the number of signatures specified. 
     The wallets must exist in the local DB"""
    tx_draft = tx_cborhex
    draft_file_name = 'tx.draft'
    draft_path = node.TRANSACTION_PATH_FILE + '/'
    path_utils.save_metadata(draft_path, draft_file_name, tx_draft)
    sign_file_name_array = []
    for id in signatures:
        db_wallet = db.query(dbmodels.Wallet).filter(dbmodels.Wallet.id == id).first()
        if db_wallet is None:
            raise HTTPException(status_code=404, detail="Wallet not found")
        payment_skey = db_wallet.payment_skey
        sign_file_name = 'temp_' + str(id)
        sign_path = node.KEYS_FILE_PATH + '/'
        path_utils.save_metadata(sign_path + sign_file_name + '/', sign_file_name + '.payment.skey', payment_skey)
        sign_file_name_array.append(sign_file_name)
    
    cbor_tx_file = {}
    sign_response = node.sign_transaction(sign_file_name_array)
    path_utils.remove_file(draft_path, draft_file_name)
    if sign_response is not None:
        success_flag = True
        tx_id = node.get_txid_signed()[:-1]
        tx_analysis = json.dumps(node.analyze_tx_signed())
        msg = "Transaction signed"
        for id in signatures:
            sign_file_name = 'temp_' + str(id)
            sign_path = node.KEYS_FILE_PATH + '/'
            path_utils.remove_folder(sign_path + sign_file_name)
        cbor_tx_path = draft_path
        with open(cbor_tx_path + 'tx.signed', 'r') as f:
            cbor_tx_file = json.load(f)
        path_utils.remove_file(cbor_tx_path, 'tx.signed')
    else:
        raise HTTPException(status_code=404, detail="Problems signing the transaction")

    tx_info = {
        "msg": msg,
        "success_flag": success_flag,
        "tx_id": tx_id,
        "tx_cborhex": cbor_tx_file

    }
    return tx_info



@router.post("/submitfile", status_code=201, 
                summary="Submit the transaction",
                response_description="Tx submit"
                )
async def submit_tx_file(file: UploadFile):
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


@router.post("/submit", status_code=201, 
                summary="Submit the transaction",
                response_description="Tx submit"
                )
async def submit_tx(tx_cborhex: dict):
    """The only purpose of this endpoint is to submit a tx file already signed.\n
    **file**: the file needs to be uploaded after signed.\n
    """
    tx_signed = tx_cborhex
    sign_file_name = 'tx.signed'
    sign_path = node.TRANSACTION_PATH_FILE + '/'
    path_utils.save_metadata(sign_path, sign_file_name, tx_signed)
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

@router.post("/mint", status_code=201, 
                summary="Mint tokens under specified policyID",
                response_description="Mint confirmation"
                )
async def mint(mint_params: Mint, db: Session = Depends(get_db)) -> dict:
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
    db_wallet = db.query(dbmodels.Wallet).filter(dbmodels.Wallet.id == id).first()
    if db_wallet is None:
        raise HTTPException(status_code=404, detail="Wallet not found")
    address_origin = db_wallet.payment_addr
    payment_skey = db_wallet.payment_skey

    # (address_origin, payment_vkey) = dblib.get_address_origin('wallet', id)
    sign_file_name = 'temp_' + id
    sign_path = node.KEYS_FILE_PATH + '/'
    sign_file_name = 'temp_' + id
    path_utils.save_file(sign_path + sign_file_name + '/', sign_file_name + '.payment.skey', payment_skey)
    address_destin = mint_params.address_destin
    address_destin_dict = [item.dict() for item in address_destin]

    script_id = mint_params.script_id
    tokens = [item.dict() for item in mint_params.tokens]

    # Check if script exists in db
    db_script = db.query(dbmodels.Scripts).filter(dbmodels.Scripts.id == script_id).first()

    if db_script is not None:
        purpose = db_script.purpose
        if purpose == 'mint':
            simple_script = db_script.content
            policyID = db_script.policyID

            # Extract the time rule from the script if any
            script_field = simple_script.get("scripts", None)
            validity_interval = None
            # Asuming a simple script with just one item inside the script field
            if script_field is not None:
                for fields in script_field:
                    print("HOLA", fields)
                    for k, v in fields.items():
                        print(k, v)
                        if v in ["before", "after"]:
                            type_time = v
                            slot = fields["slot"]
                            validity_interval = {"slot": slot, "type": type_time}
                        else:
                            msg = "Check validity interval fields"
                            mint = None
            
                # Create the script file
                script_name = db_script.name + '.script'
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
            # TODO: Make transaction for multisig option
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
    tx_id = node.get_txid_body()

    if build_response is not None:
        success_flag = True
        fees = build_response.split(' ')[-1][:-1]
        sign_response = node.sign_transaction([sign_file_name])
        if sign_response is not None:
            tx_id = node.get_txid_signed()[:-1]
            tx_analysis = json.dumps(node.analyze_tx_signed())
            submit_response = node.submit_transaction()
            msg = "Transaction signed and submit"
            # Remove temp files
            path_utils.remove_folder(sign_path + sign_file_name)
            cbor_tx_path = base.Starter(config_path).TRANSACTION_PATH_FILE + '/tx.signed'
            with open(cbor_tx_path, 'r') as file:
                cbor_tx_file = json.load(file)
        else:
            raise HTTPException(status_code=404, detail="Problems signing the transaction")
    else:
        raise HTTPException(status_code=404, detail="Problems building the transaction")
    
    # Check if transaction is already stored in db
    db_transaction = db.query(dbmodels.Transactions).filter(dbmodels.Transactions.tx_id == tx_id).first()
    if db_transaction is None:
        db_transaction = dbmodels.Transactions(
            id_wallet = id,
            address_origin = params["address_origin"],
            address_destin = str(params["address_destin"]),
            tx_cborhex = cbor_tx_file,
            metadata_info = params["metadata"],
            fees = fees,
            network = base.Starter(config_path).CARDANO_NETWORK,
            processed = success_flag,
            tx_id = tx_id
        )
        db.add(db_transaction)
        db.commit()
        db.refresh(db_transaction)
    else:
        raise HTTPException(status_code=404, detail="Transaction id already exists in database")
    return db_transaction