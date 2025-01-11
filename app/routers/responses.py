import datetime
import os
from typing import Annotated, Optional

from fastapi import APIRouter, HTTPException
from sqlmodel import Column  # pyright: ignore[reportUnknownVariableType]
from sqlmodel import (
    DateTime,
    Field,
    Relationship,
    Session,
    SQLModel,
    column,
    select,
    text,
)

from ..dependencies import AuthDep, SessionDep

router = APIRouter()


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


@router.get("/", response_model=list[ResponsePublic])
def read_responses(session: Annotated[Session, SessionDep], _: Annotated[str, AuthDep]):
    responses = session.exec(select(Response).where(Response.active == True)).all()
    return responses


@router.get("/{response_id}", response_model=ResponsePublic)
def read_response(
    response_id: int,
    session: Annotated[Session, SessionDep],
    _: Annotated[str, AuthDep],
):
    response = session.get(Response, response_id)
    if not response:
        raise HTTPException(status_code=404, detail="Response not found")

    return response


@router.post("/", response_model=ResponsePublic)
def create_response(
    response: ResponseCreate,
    session: Annotated[Session, SessionDep],
):
    db_response = Response.model_validate(response)
    db_response.time = datetime.datetime.now()
    session.add(db_response)
    session.commit()
    session.refresh(db_response)

    query = text(
        """
        UPDATE Guest
        SET response_id = :response_id
        WHERE name = :name;
    """
    )

    session.exec(
        query.bindparams(response_id=db_response.response_id, name=db_response.name)
    )
    session.commit()

    return db_response


@router.patch("/{response_id}", response_model=ResponsePublic)
def update_response(
    response_id: int,
    response: Response,
    session: Annotated[Session, SessionDep],
    _: Annotated[str, AuthDep],
):
    response_db = session.get(Response, response_id)
    if not response_db:
        raise HTTPException(status_code=404, detail="Response not found")

    response_data = response.model_dump(exclude_unset=True)
    _ = response_db.sqlmodel_update(response_data)

    session.add(response_db)
    session.commit()
    session.refresh(response_db)

    return response_db


@router.delete("/{response_id}")
def delete_response(
    response_id: int,
    session: Annotated[Session, SessionDep],
    _: Annotated[str, AuthDep],
):
    response_db = session.get(Response, response_id)
    if not response_db:
        raise HTTPException(status_code=404, detail="Response not found")

    response_db.active = False
    session.add(response_db)
    session.commit()


@router.delete("/")
def delete_all(
    session: Annotated[Session, SessionDep], passkey: str, _: Annotated[str, AuthDep]
):
    if passkey != os.getenv("DEL_PSK"):
        raise HTTPException(status_code=403, detail="Forbidden: Invalid passkey")

    responses = session.exec(select(Response)).all()
    for response in responses:
        session.delete(response)

    session.commit()
