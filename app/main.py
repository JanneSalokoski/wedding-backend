"""api.py - fastapi implementation of the wedding-site api"""

from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

from .database import create_db_and_tables
from .routers import auth_router, guests_router, progress_router, responses_router


@asynccontextmanager
async def lifespan(app: FastAPI):  # pyright: ignore[reportUnusedParameter]
    create_db_and_tables()
    _ = load_dotenv()
    yield


app: FastAPI = FastAPI(
        lifespan=lifespan,
        root_path="/",
        servers=[
            {
                "url": "https://api.jannejaroosa.fi",
                "description": "Production"
            }
        ]
        )

#origins = ["https://www.jannejaroosa.fi", "https://api.jannejaroosa.fi"]
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "www.jannejaroosa.fi", "api.jannejaroosa.fi", "*"]
)

#app.add_middleware(HTTPSRedirectMiddleware)

app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(guests_router, prefix="/guests", tags=["Guests"])
app.include_router(responses_router, prefix="/responses", tags=["Responses"])
app.include_router(progress_router, prefix="/progress", tags=["Progress"])
