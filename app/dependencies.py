import os
from typing import Annotated

import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session

from .database import get_session

_ = load_dotenv()
SECRET_KEY = os.getenv("SECRET")
ALGORITHM = "HS256"

SessionDep: Annotated[Session, Depends(get_session)] = Depends(get_session)

auth_scheme = OAuth2PasswordBearer(
        tokenUrl="https://api.jannejaroosa.fi/auth/login")


def validate_token(token: str = Depends(auth_scheme)) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


AuthDep: Annotated[dict, Depends(validate_token)] = Depends(validate_token)
