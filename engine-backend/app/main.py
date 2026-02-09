"""Engine-Backend — Control API and Dashboard for ActuallyOpenSnow Engine."""

from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from db.models import Base
from db.session import get_engine, get_session_factory

from app.routes.jobs import router as jobs_router
from app.routes.extraction import router as extraction_router
from app.routes.dashboard import router as dashboard_router

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/actuallyopensnow"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database connection on startup."""
    engine = get_engine(DATABASE_URL)
    Base.metadata.create_all(engine)
    app.state.session_factory = get_session_factory(engine)
    app.state.engine = engine
    yield
    engine.dispose()


app = FastAPI(
    title="ActuallyOpenSnow Engine API",
    description="Control API and dashboard for the GRIB2 processing engine",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(jobs_router, prefix="/api/engine")
app.include_router(extraction_router, prefix="/api/engine")
app.include_router(dashboard_router)


@app.get("/api/engine/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "engine-backend"}
