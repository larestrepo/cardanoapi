from fastapi import APIRouter

from cardanopythonlib import base
from routers.api_v1.endpoints.pydantic_schemas import NodeCommandName

router = APIRouter()

config_path = './config.ini' # Optional argument
# config_path = './cardanoapi/config.ini' # Optional argument
starter = base.Starter(config_path)
node = base.Node(config_path) # Or with the default ini: node = base.Node()

@router.get("/status", 
                summary="This is the query tip to the blockchain",
                response_description="query tip"
                )
async def check_status():
    """It returns basic info about the status of the blockchain"""
    return node.query_tip_exec()

@router.get("/protocolParams",
                summary="Protocol parameters",
                response_description="Protocol parameters"
                )
async def query_protocolParams():
    """It returns the protocol parameters of the blockchain"""
    return node.query_protocol()

@router.get("/address/{command_name}/{address}", 
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