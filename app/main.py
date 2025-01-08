"""api.py - fastapi implementation of the wedding-site api"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import create_db_and_tables
from .routers import progress_router, responses_router


@asynccontextmanager
async def lifespan(app: FastAPI):  # pyright: ignore[reportUnusedParameter]
    create_db_and_tables()
    yield


app: FastAPI = FastAPI(lifespan=lifespan)

origins = ["https://www.jannejaroosa.fi"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(progress_router, prefix="/progress", tags=["Progress"])
app.include_router(responses_router, prefix="/responses", tags=["Responses"])
