from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session

from .database import get_session

SessionDep: Annotated[Session, Depends(get_session)] = Depends(get_session)

auth_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")
AuthDep: Annotated[OAuth2PasswordBearer, Depends(auth_scheme)] = Depends(auth_scheme)
