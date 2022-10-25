from codecs import backslashreplace_errors
import enum

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql.expression import null
from sqlalchemy.dialects.postgresql import UUID, JSON

from ..dblib import Base
from .mixins import Timestamp
import uuid

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

class User(Timestamp, Base):
    __tablename__ = "users"

    # id = Column(Integer, primary_key=True, index=True)
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    id_wallet = Column(UUID(as_uuid=True), ForeignKey('wallet.id'), nullable=True)
    username = Column(String(100), nullable=False)
    hashed_password = Column(String)
    is_verified = Column(Boolean, default=False)

    wallet = relationship("Wallet", back_populates="user")

    # profile = relationship("Profile", back_populates="owner", uselist=False)

    # profile = relationship("Profile", back_populates="owner", uselist=False)
    # student_courses = relationship("StudentCourse", back_populates="student")
    # student_content_blocks = relationship(
    #     "CompletedContentBlock", back_populates="student")




# class Profile(Timestamp, Base):
#     __tablename__ = "profiles"

#     id = Column(Integer, primary_key=True, index=True)
#     first_name = Column(String(50), nullable=False)
#     last_name = Column(String(50), nullable=False)
#     bio = Column(Text, nullable=True)
#     user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

#     owner = relationship("User", back_populates="profile")
