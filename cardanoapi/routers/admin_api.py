from fastapi import APIRouter, Depends
from typing import List
from sqlalchemy.orm import Session

from db.dblib import get_db
from routers import pydantic_schemas
from db.models import dbmodels

router = APIRouter()


@router.get("/users",
                tags=["Users"],
                summary="Get all the users stored in local database",
                response_description="List of users",
                response_model=List[pydantic_schemas.User])
async def get_users(skip: int= 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(dbmodels.User).offset(skip).limit(limit).all()

@router.post("/users/", 
                tags=["Users"],
                summary="Create User",
                response_description="User created",
                response_model=pydantic_schemas.User)
async def create_user(user: pydantic_schemas.UserCreate, db: Session = Depends(get_db)):
    fake_hashed_password = user.password + "notreallyhashed"
    db_user = dbmodels.User(username=user.username, hashed_password=fake_hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# @router.get("/users/{user_id}", response_model=User)
# async def read_user(user_id: int, db: Session = Depends(get_db)):
#     db_user = get_user(db=db, user_id=user_id)
#     if db_user is None:
#         raise HTTPException(status_code=404, detail="User not found")
#     return db_user