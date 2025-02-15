import os
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from passlib.hash import argon2
from pydantic import BaseModel
from sqlmodel import Field  # pyright: ignore[reportUnknownVariableType]
from sqlmodel import Session, SQLModel, select, text

from ..dependencies import AuthDep, SessionDep

router = APIRouter()

_ = load_dotenv()
SECRET_KEY = os.getenv("SECRET")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class UserBase(SQLModel):
    username: str = Field(index=True)


class User(UserBase, table=True):
    user_id: int | None = Field(primary_key=True, default=None)
    hashed_password: str = Field()
    disabled: bool = Field(default=False)


class CreateUser(UserBase):
    password: str


class PublicUser(UserBase):
    hashed_password: str

class Login(BaseModel):
    username: str
    password: str


def verify_password(plain_password: str, hashed_password: str) -> str:
    return argon2.verify(  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        plain_password, hashed_password
    )


def get_password_hash(password: str) -> str:
    return argon2.hash(  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        password
    )


def get_user(username: str) -> User | None:
    session: Annotated[Session, SessionDep] = SessionDep
    user: User | None = session.exec(
        select(User).where(User.username == username)
    ).one_or_none()
    return user


def authenticate_user(user: User, password: str) -> bool:
    if not verify_password(password, user.hashed_password):
        return False

    return True


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode: dict = data.copy()
    if expires_delta:
        expire: datetime = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)

    _ = load_dotenv()
    SECRET_KEY = os.getenv("SECRET")

    to_encode.update({"exp": expire})
    print("secret", SECRET_KEY)
    encoded_jwt: str = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


@router.post("/login/")
async def login_json(
    login_data: Login,
    session: Annotated[Session, SessionDep],
    #response: Response
) -> Token:
    username = login_data.username
    password = login_data.password

    user = session.exec(select(User).where(User.username == username)).one_or_none()

    if not user or not authenticate_user(user, password):
        raise HTTPException(
            status_code=400,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    return Token(access_token=access_token, token_type="bearer")


async def get_current_user(token: Annotated[str, AuthDep]):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(  # pyright: ignore[reportUnknownMemberType, reportAny]
            token, SECRET_KEY, algorithms=[ALGORITHM]
        )

        username: str | None = payload.get("sub")  # pyright: ignore[reportAny]

        if username is None:
            raise credentials_exception

        token_data = TokenData(username=username)

    except InvalidTokenError:
        raise credentials_exception

    user: User = get_user(fake_users_db, username=token_data.username)
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")

    return current_user


@router.post("/token")
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[Session, SessionDep],
) -> Token:
    username = form_data.username
    password = form_data.password

    user = session.exec(select(User).where(User.username == username)).one_or_none()

    if not user or not authenticate_user(user, password):
        raise HTTPException(
            status_code=400,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    return Token(access_token=access_token, token_type="bearer")


@router.post("/users", response_model=PublicUser)
def create_user(
    userData: CreateUser,
    session: Annotated[Session, SessionDep],
    _: Annotated[str, AuthDep],
):
    user = User(
        username=userData.username, hashed_password=get_password_hash(userData.password)
    )

    db_user = User.model_validate(user)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


@router.patch(
    "/users",
    response_model=PublicUser,
)
def update_user(
    userData: CreateUser,
    session: Annotated[Session, SessionDep],
    _: Annotated[str, AuthDep],
):
    user: User | None = session.exec(
        select(User).where(User.username == userData.username)
    ).one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user_data = userData.model_dump(exclude_unset=True)
    _ = user.sqlmodel_update(user_data)

    session.add(user)
    session.commit()
    session.refresh(user)

    return user


@router.delete("/users")
def delete_all(
    session: Annotated[Session, SessionDep], passkey: str, _: Annotated[str, AuthDep]
):
    if passkey != os.getenv("DEL_PSK"):
        raise HTTPException(status_code=403, detail="Forbidden: Invalid passkey")

    users = session.exec(select(User)).all()
    for user in users:
        session.delete(user)

    session.commit()
