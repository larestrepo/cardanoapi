from enum import Enum
from typing import List, Union, Optional
from datetime import datetime
from pydantic import UUID4

from pydantic import BaseModel, validator

class UserBase(BaseModel):
    username: str

class User(UserBase):
    id: UUID4
    id_wallet: Optional[str]=None
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

        
class UserCreate(UserBase):
    password: str

class NodeCommandName(str, Enum):
    utxos = "utxos"
    balance = "balance"

class KeyCreate(BaseModel):
    name: Union [str, None]
    size: int = 24
    save_flag: bool = True

class KeyRecover(BaseModel):
    name: Union [str, None]
    words: List[str]
    save_flag: bool = True

class AddressDestin(BaseModel):
    address: str
    amount: int

class SimpleSend(BaseModel):
    wallet_id: str
    address_destin: list[AddressDestin]
    metadata: Union [dict, None] = None
    witness: int = 1

class BuildTx(BaseModel):
    address_origin: str
    address_destin: list[AddressDestin]
    metadata: Union [dict, None] = None
    witness: int = 1

class Tokens(BaseModel):
    name: str
    amount: int

class Mint(SimpleSend):
    script_id: str
    tokens: list[Tokens]

class Script(BaseModel):
    name: str
    type: str = "all"
    required: int = 0
    hashes: List[str]
    type_time: str = ""
    slot: int = 0

    @validator("type", always=True)
    def check_type(cls, value):
        if value not in ("sig", "all", "any", "atLeast"):
            raise ValueError("type must be: sig, all, any or atLeast ")
        return value

    @validator("required", always=True)
    def check_required(cls, value, values):
        if values["type"] == "atLeast":
            assert isinstance(value, int), "Required field must be integer if type atLeast is used"
            assert value > 0, "Required field must be higher than 0 and be equal to the number of specified keyHashes"
        return value
    
    @validator("hashes", always=True)
    def check_hashes(cls, value, values):
        if values["type"] == "atLeast":
            assert len(value) >= values["required"], "Number of keyshashes should be atLeast equal to the number of required keyHashes"
        return value
    
    @validator("slot", always=True)
    def check_slot(cls, value, values):
        if values["type_time"] in ("before", "after"):
            assert isinstance(value, int), "Slot field must be integer if type before/after is used"
            assert value > 0, "At least it should be greater than 0 or the current slot number"
            return value
        else:
            return None

class ScriptPurpose(str, Enum):
    mint = "mint"
    multisig = "multisig"