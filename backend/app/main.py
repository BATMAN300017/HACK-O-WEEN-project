import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.core.config import settings
from app.core.database import init_db
from app.core.logging import setup_logging, logger
from app.api.router import api_router

setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="SentinelFlow AI — The Self-Directed Fraud Investigation Platform Backend API",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
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

# Root health check endpoint
@app.get("/health", tags=["Health"])
def root_health():
    return {"status": "ok", "app": settings.PROJECT_NAME, "version": settings.VERSION}

# Mount static files and dashboard
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/", include_in_schema=False)
    @app.get("/app", include_in_schema=False)
    def serve_dashboard():
        index_file = os.path.join(static_dir, "index.html")
        return FileResponse(index_file)

@app.on_event("startup")
def on_startup():
    logger.info("SentinelFlow AI starting up...")
    init_db()
    # Auto-seed initial demo records if database is fresh
    try:
        from app.core.database import get_db_connection
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM transactions")
            count = cursor.fetchone()[0]
            if count == 0:
                logger.info("Fresh database detected. Auto-seeding initial demo records...")
                from scripts.seed_demo_data import seed_demo_database
                seed_demo_database()
            else:
                logger.info(f"Database contains {count} transactions. Ready.")
    except Exception as e:
        logger.warning(f"Startup database check: {e}")
    logger.info("Database and services initialized successfully.")
