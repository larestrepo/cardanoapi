from fastapi import APIRouter

from cardanopythonlib import base
from routers.pydantic_schemas import KeyCreate, KeyRecover
from db import dblib

router = APIRouter()

config_path = './config.ini' # Optional argument
starter = base.Starter(config_path)
keys = base.Keys(config_path) # Or with the default ini: node = base.Node()

@router.post("/cardanodatos/keys/generate", status_code=201, 
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

@router.post("/cardanodatos/keys/mnemonics", status_code=201, 
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

@router.post("/cardanodatos/keys/recover", status_code=201, 
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