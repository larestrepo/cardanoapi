import json
from fastapi import APIRouter, UploadFile, Depends
from sqlalchemy.orm import Session

from cardanopythonlib import base, path_utils
from routers.api_v1.endpoints.pydantic_schemas import ScriptPurpose, Script
from db.dblib import get_db
from db.models import dbmodels

router = APIRouter()

config_path = './config.ini' # Optional argument
# config_path = './cardanoapi/config.ini' # Optional argument
starter = base.Starter(config_path)
node = base.Node(config_path) # Or with the default ini: node = base.Node()


@router.post("/uploadScript/{script_purpose}", status_code=201, 
                summary="Upload an existing script file",
                response_description="Script uploaded"
                )
async def upload_script(script_name: str, 
        file: UploadFile, 
        script_purpose: ScriptPurpose,
        db: Session = Depends(get_db)):
    """Upload script file and stores it in local db. Purpose: mint, multisig\n
    **file**: script file to be uploaded.\n
    """
    script_content = await file.read()
    script_file_path = node.MINT_FOLDER
    script_content = json.loads(script_content)
    path_utils.save_metadata(script_file_path, script_name, script_content)
    policyID = node.create_policy_id(script_purpose, script_name)
    if policyID is None:
        db_script = {"msg": "Problems building the script"}
    else:
        db_script = dbmodels.Scripts(
            name = script_name,
            purpose = script_purpose,
            content = script_content,
            policyID = policyID
        )
        db.add(db_script)
        db.commit()
        db.refresh(db_script)

    return db_script

@router.post("/simplescript/{script_purpose}", status_code=201, 
                summary="",
                response_description="Script creation"
                )
async def simpleScript(simpleScript_params: Script, 
    script_purpose: ScriptPurpose,
    db: Session = Depends(get_db)) -> dict:
    """Creation of a script depending of its purpose: mint or multisig.\n
    **name**: name of the script.\n
    **type**: type of the script. Options are: all, any, atLeast.\n
    **required**: if script type is atLeast, number of required signers must be provided.\n
    **hashes**: list of pubKeyHashes.\n
    **type_time**: if script constraint by time. Options are: before, after.\n
    **slot**: slot for the validity range.
    """
    script_name = simpleScript_params.name
    type = simpleScript_params.type
    required = simpleScript_params.required
    hashes = simpleScript_params.hashes
    type_time = simpleScript_params.type_time
    slot = simpleScript_params.slot
    parameters = {
        "name": script_name,
        "type": type,
        "required": required,
        "hashes": hashes,
        "type_time": type_time,
        "slot": slot,
        "purpose": script_purpose
    }
    simple_script, policyID = node.create_simple_script(parameters=parameters)
    if simple_script is None or policyID is None:
        db_script = {"msg": "Problems building the script"}
    else:
        script_purpose = script_purpose._value_
        db_script = dbmodels.Scripts(
            name = script_name,
            purpose = script_purpose,
            content = simple_script,
            policyID = policyID,
            type = type,
            required = required,
            hashes = hashes,
            type_time = type_time,
            slot = slot
        )
        db.add(db_script)
        db.commit()
        db.refresh(db_script)
    
    script_file_path = ''
    if script_purpose == 'mint':
        script_file_path = node.MINT_FOLDER
    elif script_purpose == 'multisig':
        script_file_path = node.MULTISIG_FOLDER

    script_file_name = '/' + script_name + '.script'
    policy_file_name = '/' + script_name + '.policyid'
    path_utils.remove_file(script_file_path, script_file_name)
    path_utils.remove_file(script_file_path, policy_file_name)
    return db_script
