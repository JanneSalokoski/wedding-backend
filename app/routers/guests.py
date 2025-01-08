import datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException
from sqlmodel import Field  # pyright: ignore[reportUnknownVariableType]
from sqlmodel import Relationship, Session, SQLModel, column, select

from ..dependencies import SessionDep
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
def read_progress(session: Annotated[Session, SessionDep]):
    results = session.exec(
        select(Guest, Response)
        .join(Response, Guest.response_id == Response.response_id)
        .where(Guest.active == True)
    ).all()

    public: list[GuestPublic] = []
    for guest, response in results:
        guest_public = GuestPublic(
            guest_id=guest.guest_id,
            name=guest.name,
            group=guest.group,
            diet=response.diet,
            rsvp=response.rsvp,
            time=response.time,
        )
        public.append(guest_public)

    return public


@router.post("/", response_model=GuestPublic)
def create_guest(guest: GuestCreate, session: Annotated[Session, SessionDep]):
    db_response = Guest.model_validate(guest)
    session.add(db_response)
    session.commit()
    session.refresh(db_response)
    return db_response


@router.post("/{guest_id}")
def link_response(
    data: GuestLink, guest_id: int, session: Annotated[Session, SessionDep]
):
    guest = session.get(Guest, guest_id)
    guest.response_id = data.response_id
    session.add(guest)
    session.commit()
    session.refresh(guest)

    return guest


@router.delete("/{guest_id}")
def delete_guest(guest_id: int, session: Annotated[Session, SessionDep]):
    response_db = session.get(Guest, guest_id)
    if not response_db:
        raise HTTPException(status_code=404, detail="Response not found")

    response_db.active = False
    session.add(response_db)
    session.commit()


@router.delete("/")
def delete_all(session: Annotated[Session, SessionDep]):
    guests = session.exec(select(Guest)).all()

    for guest in guests:
        session.delete(guest)

    session.commit()
