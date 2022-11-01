from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from cardanopythonlib import base
from routers.api_v1.endpoints.pydantic_schemas import KeyCreate, KeyRecover
from db.dblib import get_db
from db.models import dbmodels
import uuid

router = APIRouter()

config_path = './config.ini' # Optional argument
starter = base.Starter(config_path)
keys = base.Keys(config_path) # Or with the default ini: node = base.Node()

@router.post("/generate", status_code=201, 
                summary="Create wallet using mnemonics as root key",
                response_description="Keys generated"
                )
async def create_keys(key: KeyCreate, db: Session = Depends(get_db)) -> dict:
    """Generate full wallet with mnemonics, cardano keys and base address
        This method does not store any wallet info if the save_flag is False
        If the save_flag is True, cardano cli skeys are stored in local db.\n
        **name**: wallet name if to be stored in local db.\n
        **size**: mnemonic size (12, 15, 24).\n
        **save_flag**: If to be stored in local db. It only stores cardano cli skeys to sign transactions
    """
    if key.name is None:
        key.name = "WalletDummyName" + str(uuid.uuid4)

    key_created = keys.deriveAllKeys(key.name, size = key.size, save_flag = key.save_flag)
    db_key = dbmodels.Wallet(
        name=key.name,
        base_addr=key_created.get("base_addr"),
        payment_addr=key_created.get("payment_addr"),
        payment_skey=key_created.get("payment_skey"),
        payment_vkey=key_created.get("payment_vkey"),
        stake_addr=key_created.get("stake_addr"),
        stake_skey=key_created.get("stake_skey"),
        stake_vkey=key_created.get("stake_vkey"),
        hash_verification_key=key_created.get("hash_verification_key"),
    )
    if key.save_flag:
        db.add(db_key)
        db.commit()
        db.refresh(db_key)
    return db_key

@router.post("/mnemonics", status_code=201, 
                summary="Generate mnemonics only",
                response_description="mnemonics generated"
                )
async def generate_mnemonics(size: int = 24) -> list:
    """It generates the mnemonics only. This method never stores
            any info in local db.\n
        **size**: mnemonic size (12, 15, 24).
    """
    return keys.generate_mnemonic(size)

@router.post("/recover", status_code=201, 
                summary="Recover wallet by using mnemonics",
                response_description="Recover keys info"
                )
async def recover_keys(key: KeyRecover, db: Session = Depends(get_db)) -> dict:
    """Generate full wallet cardano keys and base address from mnemonics\n
    **name**: wallet name if to be stored in local db.\n
    **words**: The mnemonic list\n
    **save_flag**: If stored in local db. It only stores cardano cli skeys to sign transactions
    """
    if key.name is None:
        key.name = "WalletDummyName"
    key_created = keys.deriveAllKeys(key.name, words = key.words, save_flag = key.save_flag)
    db_key = dbmodels.Wallet(
        name=key.name,
        base_addr=key_created.get("base_addr"),
        payment_addr=key_created.get("payment_addr"),
        payment_skey=key_created.get("payment_skey"),
        payment_vkey=key_created.get("payment_vkey"),
        stake_addr=key_created.get("stake_addr"),
        stake_skey=key_created.get("stake_skey"),
        stake_vkey=key_created.get("stake_vkey"),
        hash_verification_key=key_created.get("hash_verification_key"),
    )
    if key.save_flag:
        db.add(db_key)
        db.commit()
        db.refresh(db_key)
    return db_key