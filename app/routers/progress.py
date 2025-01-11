import os
from typing import Annotated

from fastapi import APIRouter, HTTPException
from sqlalchemy import func
from sqlmodel import Field  # pyright: ignore[reportUnknownVariableType]
from sqlmodel import Session, SQLModel, select

from ..dependencies import AuthDep, SessionDep

router = APIRouter()


class ProgressBase(SQLModel):
    timestamp: int = Field()
    headline: str = Field(index=True)


class Progress(ProgressBase, table=True):
    progress_id: int | None = Field(primary_key=True, default=None)


class ProgressAvg(SQLModel):
    headline: str = Field()
    average: float = Field()


class ProgressCount(SQLModel):
    headline: str = Field()
    amount: int = Field()


class ProgressStat(SQLModel):
    headline: str = Field()
    amount: int = Field()
    average: float = Field()


@router.get("/", response_model=list[ProgressBase])
def read_progress(session: Annotated[Session, SessionDep]):
    progresses = session.exec(select(Progress)).all()
    return progresses


@router.get("/avg/", response_model=list[ProgressAvg])
def read_progress_averages(session: Annotated[Session, SessionDep]):
    averages = func.avg(Progress.timestamp).label("average")
    progresses = session.exec(
        select(Progress.headline, averages)
        .group_by(Progress.headline)
        .order_by(averages.desc())
    ).all()
    return progresses


@router.get("/count/", response_model=list[ProgressCount])
def read_progress_counts(
    session: Annotated[Session, SessionDep], _: Annotated[str, AuthDep]
):
    counts = func.count(Progress.headline).label(  # pyright: ignore[reportArgumentType]
        "amount"
    )
    progresses = session.exec(
        select(Progress.headline, counts)
        .group_by(Progress.headline)
        .order_by(counts.desc())
    ).all()
    return progresses


@router.get("/stats/", response_model=list[ProgressStat])
def read_progress_stats(session: Annotated[Session, SessionDep]):
    averages = func.avg(Progress.timestamp).label("average")
    counts = func.count(Progress.headline).label(  # pyright: ignore[reportArgumentType]
        "amount"
    )
    progresses = session.exec(
        select(Progress.headline, counts, averages)
        .group_by(Progress.headline)
        .order_by(counts.desc())
    ).all()
    return progresses


@router.post("/")
def create_progress(
    progress: ProgressBase,
    session: Annotated[Session, SessionDep],
):
    db_progress = Progress.model_validate(progress)
    session.add(db_progress)
    session.commit()
    session.refresh(db_progress)

    return db_progress


@router.delete("/")
def delete_all(
    session: Annotated[Session, SessionDep], passkey: str, _: Annotated[str, AuthDep]
):
    if passkey != os.getenv("DEL_PSK"):
        raise HTTPException(status_code=403, detail="Forbidden: Invalid passkey")

    progresses = session.exec(select(Progress)).all()
    for progress in progresses:
        session.delete(progress)

    session.commit()
