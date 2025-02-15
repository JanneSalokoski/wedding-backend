import datetime
import os
from ast import Param
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException
from sqlalchemy.orm import selectinload
from sqlmodel import Field  # pyright: ignore[reportUnknownVariableType]
from sqlmodel import Relationship, Session, SQLModel, column, select, text
from starlette.types import HTTPExceptionHandler

from ..dependencies import AuthDep, SessionDep
from .responses import Response

router = APIRouter()


class GuestBase(SQLModel):
    name: str = Field(index=True)
    group: str = Field(index=True)


class Guest(GuestBase, table=True):
    guest_id: int | None = Field(primary_key=True, default=None)
    response_id: int | None = Field(foreign_key="response.response_id", default=None)
    active: bool | None = Field(default=True)


class GuestPublic(GuestBase):
    guest_id: int | None = Field(primary_key=True, default=None)
    diet: str | None = Field(default=None)
    rsvp: bool = Field(default=False)
    time: datetime.datetime | None = Field(default=None)


class GuestCreate(SQLModel):
    name: str = Field()
    group: str = Field()


class GuestLink(SQLModel):
    response_id: int = Field()


@router.get("/", response_model=list[GuestPublic])
def read_guests(session: Annotated[Session, SessionDep], _: Annotated[str, AuthDep]):
    query = text(
        """
        SELECT g.guest_id, g.name, g.'group', r.diet, COALESCE(rsvp, FALSE) AS rsvp, r.time
        FROM Guest as g
        LEFT JOIN Response as r ON g.response_id = r.response_id;
    """
    )
    res: list[GuestPublic] = session.exec(query).all()
    return res


@router.get("/{guest_id}", response_model=GuestPublic)
def read_guest(
    guest_id: int, session: Annotated[Session, SessionDep], _: Annotated[str, AuthDep]
):
    query = text(
        """
        SELECT g.guest_id, g.name, g.'group', r.diet, COALESCE(rsvp, FALSE) AS rsvp, r.time
        FROM Guest as g
        LEFT JOIN Response as r ON g.response_id = r.response_id
        WHERE g.guest_id = :guest_id;
    """
    )
    res: GuestPublic = session.exec(query.bindparams(guest_id=guest_id)).one()
    return res


@router.post("/", response_model=GuestPublic)
def create_guest(
    guest: GuestCreate,
    session: Annotated[Session, SessionDep],
    _: Annotated[str, AuthDep],
):
    db_response = Guest.model_validate(guest)
    session.add(db_response)
    session.commit()
    session.refresh(db_response)
    return db_response


@router.post("/many/", response_model=list[GuestPublic])
def create_guests(
    guests: list[GuestCreate],
    session: Annotated[Session, SessionDep],
    _: Annotated[str, AuthDep],
):
    for guest in guests:
        db_response = Guest.model_validate(guest)
        session.add(db_response)
        session.commit()
        session.refresh(db_response)

    return guests


@router.post("/{guest_id}")
def link_response(
    data: GuestLink,
    guest_id: int,
    session: Annotated[Session, SessionDep],
    _: Annotated[str, AuthDep],
):
    guest = session.get(Guest, guest_id)
    guest.response_id = data.response_id
    session.add(guest)
    session.commit()
    session.refresh(guest)

    return guest


@router.delete("/{guest_id}")
def delete_guest(
    guest_id: int, session: Annotated[Session, SessionDep], _: Annotated[str, AuthDep]
):
    response_db = session.get(Guest, guest_id)
    if not response_db:
        raise HTTPException(status_code=404, detail="Response not found")

    response_db.active = False
    session.add(response_db)
    session.commit()


@router.delete("/")
def delete_all(
    session: Annotated[Session, SessionDep], passkey: str, _: Annotated[str, AuthDep]
):
    guests = session.exec(select(Guest)).all()

    print(os.getenv("DEL_PSK"))
    if passkey != os.getenv("DEL_PSK"):
        raise HTTPException(status_code=403, detail="Forbidden: Invalid passkey")

    for guest in guests:
        session.delete(guest)

    session.commit()
