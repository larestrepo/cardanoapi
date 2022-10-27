from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import List
from sqlalchemy.orm import Session

from db.dblib import get_db
from routers import pydantic_schemas
from db.models import dbmodels

from pydantic import UUID4

router = APIRouter()

@router.get("/users",
        tags=["Users"],
        summary="Get all the users stored in local database",
        response_description="List of users",
        response_model=List[pydantic_schemas.User])
def get_users(skip: int= 0, limit: int = 100, db: Session = Depends(get_db)):
    db_user = db.query(dbmodels.User).offset(skip).limit(limit).all()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router.get("/users/{user_id}",
        tags=["Users"],
        summary="Get user by id",
        response_description="User by id",
        response_model=pydantic_schemas.User)
def get_user_by_id(user_id: UUID4, db: Session = Depends(get_db)):
    db_user = db.query(dbmodels.User).filter(dbmodels.User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router.get("/users/wallet/{id_wallet}",
        tags=["Users"],
        summary="Get user by wallet id",
        response_description="User by wallet id",
        response_model=pydantic_schemas.User)
def get_user_by_wallet_id(id_wallet: UUID4, db: Session = Depends(get_db)):
    db_user = db.query(dbmodels.User).filter(dbmodels.User.id_wallet == id_wallet).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router.post("/users/", 
                tags=["Users"],
                summary="Create User",
                response_description="User created",
                response_model=pydantic_schemas.User)
def create_user(user: pydantic_schemas.UserCreate, db: Session = Depends(get_db)):
    fake_hashed_password = user.password + "notreallyhashed"
    db_user = dbmodels.User(username=user.username, hashed_password=fake_hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user