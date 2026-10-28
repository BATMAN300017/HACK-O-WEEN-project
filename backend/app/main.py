import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.core.config import settings, validate_production_secret_key
from app.core.database import init_db
from app.core.logging import setup_logging, logger
from app.api.router import api_router

setup_logging()

@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_production_secret_key(settings.ENVIRONMENT, settings.SECRET_KEY)
    logger.info("SentinelFlow AI starting up...")
    init_db()
    logger.info("Database and services initialized successfully.")
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="SentinelFlow AI — The Self-Directed Fraud Investigation Platform Backend API",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API v1 router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Serve the dashboard when present, otherwise provide a useful API landing response.
static_dir = os.path.join(os.path.dirname(__file__), "static")
index_file = os.path.join(static_dir, "index.html")
if os.path.isfile(index_file):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/", include_in_schema=False)
    @app.get("/app", include_in_schema=False)
    def serve_dashboard():
        return FileResponse(index_file)
else:
    @app.get("/", include_in_schema=False)
    def root():
        return {
            "status": "ok",
            "app": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "docs": "/docs",
            "health": "/health",
        }


@app.get("/health", tags=["Health"])
def root_health():
    return {"status": "ok", "app": settings.PROJECT_NAME, "version": settings.VERSION}
