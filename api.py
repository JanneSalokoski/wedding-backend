"""api.py - fastapi implementation of the wedding-site api"""

import datetime
import sqlite3
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import (
    Column,
    DateTime,
    Field,
    Sequence,
    Session,
    SQLModel,
    create_engine,
    select,
)


class ResponseBase(SQLModel):
    name: str = Field(index=True)
    diet: str | None = Field(default=None)
    rsvp: bool = Field(default=True)


class Response(ResponseBase, table=True):
    response_id: int | None = Field(default=None, primary_key=True)
    time: datetime.datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=False), nullable=False)
    )
    active: bool = Field(default=True)


class ResponsePublic(ResponseBase):
    response_id: int
    time: datetime.datetime


class ResponseCreate(ResponseBase):
    pass


sqlite_file = "database.db"
sqlite_url = f"sqlite:///{sqlite_file}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app: FastAPI = FastAPI(lifespan=lifespan)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/responses/", response_model=list[ResponsePublic])
def read_responses(session: SessionDep):
    responses = session.exec(select(Response).where(Response.active == True)).all()
    return responses


@app.get("/responses/{response_id}", response_model=ResponsePublic)
def read_response(response_id: int, session: SessionDep):
    response = session.get(Response, response_id)
    if not response:
        raise HTTPException(status_code=404, detail="Response not found")

    return response


@app.post("/responses/", response_model=ResponsePublic)
def create_response(response: ResponseCreate, session: SessionDep):
    db_response = Response.model_validate(response)
    db_response.time = datetime.datetime.now()
    session.add(db_response)
    session.commit()
    session.refresh(db_response)
    return db_response


@app.patch("/responses/{response_id}", response_model=ResponsePublic)
def update_response(response_id: int, response: Response, session: SessionDep):
    response_db = session.get(Response, response_id)
    if not response_db:
        raise HTTPException(status_code=404, detail="Response not found")

    response_data = response.model_dump(exclude_unset=True)
    _ = response_db.sqlmodel_update(response_data)

    session.add(response_db)
    session.commit()
    session.refresh(response_db)

    return response_db


@app.delete("/responses/{response_id}")
def delete_response(response_id: int, session: SessionDep):
    response_db = session.get(Response, response_id)
    if not response_db:
        raise HTTPException(status_code=404, detail="Response not found")

    response_db.active = False
    session.add(response_db)
    session.commit()
