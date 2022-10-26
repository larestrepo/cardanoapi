from codecs import backslashreplace_errors
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Column, Enum
from sqlalchemy import ForeignKey, Integer, String, Text, DateTime, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSON

from ..dblib import Base
from .mixins import Timestamp
import uuid
from routers.pydantic_schemas import ScriptPurpose


class Wallet(Timestamp, Base):
    __tablename__ = "wallet"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(Text, nullable=False)
    base_addr = Column(Text, nullable=False)
    payment_addr = Column(Text, nullable=False)
    payment_skey = Column(JSON, nullable=False)
    payment_vkey = Column(JSON, nullable=False)
    stake_addr = Column(Text, nullable=False)
    stake_skey = Column(JSON, nullable=False)
    stake_vkey = Column(JSON, nullable=False)
    hash_verification_key = Column(Text, nullable=False)

    user = relationship("User", back_populates="wallet")
    transactions = relationship("Transactions", back_populates="wallet")

class User(Timestamp, Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    id_wallet = Column(UUID(as_uuid=True), ForeignKey('wallet.id'), nullable=True)
    username = Column(String(100), nullable=False)
    hashed_password = Column(String)
    is_verified = Column(Boolean, default=False)

    wallet = relationship("Wallet", back_populates="user")

class Transactions(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    id_wallet = Column(UUID(as_uuid=True), ForeignKey('wallet.id'), nullable=True)
    submission = Column(DateTime, default=datetime.utcnow, nullable=True)
    address_origin = Column(Text, nullable=True)
    address_destin = Column(Text, nullable=True)
    tx_cborhex = Column(JSON, nullable=True)
    metadata_info = Column(JSON, nullable=True)
    fees = Column(BigInteger, nullable=True)
    network = Column(Text, nullable=True)
    processed = Column(Boolean, nullable=True)

    wallet = relationship("Wallet", back_populates="transactions")

class Scripts(Base):
    __tablename__ = "scripts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(Text, nullable=True)
    purpose = Column(Enum(ScriptPurpose), nullable=True)
    content = Column(JSON, nullable=True)
    policyID = Column(Text, nullable=True)