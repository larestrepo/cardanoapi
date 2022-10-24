import json
from fastapi import APIRouter, UploadFile

from cardanopythonlib import base, path_utils
from routers.pydantic_schemas import ScriptPurpose, Script

from db import dblib

router = APIRouter()

config_path = './config.ini' # Optional argument
starter = base.Starter(config_path)
node = base.Node(config_path) # Or with the default ini: node = base.Node()


@router.post("/cardanodatos/uploadScript/{script_purpose}", status_code=201, 
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

# @router.get("/cardanodatos/queryScript")
# async def query_script():
        
#     tableName = 'scripts'
#     query = f"SELECT * FROM {tableName};"
#     scripts = dblib.read_query(query)
#     return scripts

@router.post("/cardanodatos/simplescript/{script_purpose}", status_code=201, 
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
