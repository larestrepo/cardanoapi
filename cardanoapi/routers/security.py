from datetime import datetime, timedelta
from typing import Union

from fastapi import Depends, HTTPException, status, APIRouter
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext

from db.dblib import get_db, config
from sqlalchemy.orm import Session
from db.models import dbmodels
from routers import pydantic_schemas

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

router = APIRouter()


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
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, params["secret_key"], algorithm=params["algorithm"])
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
    return user_db


async def get_current_active_user(current_user: dbmodels.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.is_verified:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


@router.post("/token", response_model=pydantic_schemas.Token)
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
    access_token = create_access_token(
        data={"sub": user_db.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/users/me/", response_model=pydantic_schemas.User)
async def read_users_me(current_user: dbmodels.User = Depends(get_current_active_user)):
    return current_user


@router.get("/users/me/items/")
async def read_own_items(current_user: dbmodels.User = Depends(get_current_active_user)):
    return [{"item_id": "Foo", "owner": current_user.username}]