from datetime import datetime, timedelta
from typing import Union, List

from fastapi import Depends, HTTPException, status, APIRouter
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext

from db.dblib import get_db, config
from sqlalchemy.orm import Session
from db.models import dbmodels
from routers.api_v1.endpoints import pydantic_schemas
from core.config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/security/token")

router = APIRouter()

#############################################
# Security section

def verify_user_existence(username: str, db: Session):
    return db.query(dbmodels.User).filter(dbmodels.User.username == username).first()
#  user_db = db.query(dbmodels.User).filter(dbmodels.User.username == form_data.username).first()


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)

def authenticate_user(user_db, password: str):
    # Verify password and verification
    password_flag = verify_password(password, user_db.hashed_password)
    if password_flag:
        return True
    else:
        return False

def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None):
    params = config('./config.ini', section='users')
    to_encode = data.copy()
    print(data)
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, params["secret_key"], algorithm=params["algorithm"])
    print(encoded_jwt)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    params = config('./config.ini', section='users')
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, params["secret_key"], algorithms=[params["algorithm"]])
        username: str = payload["sub"]
        if username is None:
            raise credentials_exception
        token_data = pydantic_schemas.TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user_db = db.query(dbmodels.User).filter(dbmodels.User.username == token_data.username).first()
    if user_db is None:
        raise credentials_exception
    return pydantic_schemas.User.from_orm(user_db)


# async def get_current_active_user(current_user: dbmodels.User = Depends(get_current_user), db: Session = Depends(get_db)):
#     print("verification", current_user.is_verified)
#     if not current_user.is_verified:
#         raise HTTPException(status_code=400, detail="Inactive user")
#     return current_user

#############################################
# User section endpoints

@router.post("/signup/",
                summary="Create User",
                response_description="User created",
                response_model=pydantic_schemas.Token)
async def create_user(user: pydantic_schemas.UserCreate, db: Session = Depends(get_db)):
    db_user_existing = verify_user_existence(user.username, db)
    if db_user_existing is not None:
        raise HTTPException(status_code=400, detail="User already exists")

    hashed_password = get_password_hash(user.password)
    db_user = dbmodels.User(username=user.username, hashed_password=hashed_password, is_verified=True) # All users is_verified=True. To be used in future
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    # Once user is registered, create and return token
    params = config('./config.ini', section='users')
    access_token_expires = timedelta(minutes=int(params["token_expire"]))
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/token", 
    summary="Get token for registerd user",
    response_description="login succesfull",
    response_model=pydantic_schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user_db = db.query(dbmodels.User).filter(dbmodels.User.username == form_data.username).first()
    if not user_db:
        raise HTTPException(status_code=400, detail="Incorrect username")
    authenticate_flag = authenticate_user(user_db, form_data.password)
    if not authenticate_flag:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password or user not verified",
            headers={"WWW-Authenticate": "Bearer"},
        )
    params = config('./config.ini', section='users')
    access_token_expires = timedelta(minutes=int(params["token_expire"]))
    print(form_data.username)
    access_token = create_access_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/users/me/", 
    summary="Get info for user currently login",
    response_description="User info",
    response_model=pydantic_schemas.User)
async def get_user(current_user: dbmodels.User = Depends(get_current_user)):
    return current_user