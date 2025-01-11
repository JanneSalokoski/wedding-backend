import typer
from passlib.hash import argon2
from sqlmodel import Session, SQLModel, create_engine, text

from .database import get_engine

cli = typer.Typer()


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


@cli.command()
def create_user(username: str, password: str):
    """Create a new user"""

    engine = get_engine()
    with Session(engine) as session:
        try:
            query = text(
                "INSERT INTO User (username, hashed_password, disabled) VALUES (:username, :password, False);"
            )
            session.exec(
                query.bindparams(username=username, password=argon2.hash(password))
            )
            session.commit()
            typer.echo(f"User '{username}' created successfully")
        except Exception as e:
            typer.echo(f"Error: {e}")


if __name__ == "__main__":
    cli()
