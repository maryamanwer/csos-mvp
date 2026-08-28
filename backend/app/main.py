"""
CSOS backend entrypoint.
Run locally: uvicorn app.main:app --reload --port 8000
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core.config import settings
from app.services.bootstrap import initialize_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.ENVIRONMENT != "test":
        initialize_database()
    yield

app = FastAPI(
    title=settings.APP_NAME,
    description="Cyber Security Operating System (CSOS) backend",
    version="0.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

@app.get("/health")
def health():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "version": "0.3.0",
    }
