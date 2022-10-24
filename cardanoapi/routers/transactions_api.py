import json

from fastapi import APIRouter, UploadFile

from cardanopythonlib import base, path_utils
from routers.pydantic_schemas import SimpleSend, BuildTx, Mint
from db import dblib

router = APIRouter()

config_path = './config.ini' # Optional argument
starter = base.Starter(config_path)
node = base.Node(config_path) # Or with the default ini: node = base.Node()



@router.post("/cardanodatos/transactions/simplesend", status_code=201, 
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

@router.post("/cardanodatos/transactions/buildtx", status_code=201, 
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

@router.post("/cardanodatos/transactions/submit", status_code=201, 
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

@router.post("/cardanodatos/transactions/mint", status_code=201, 
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
