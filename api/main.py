import logging
import os

from dotenv import load_dotenv

load_dotenv(override=True)

from fastapi import FastAPI  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from prometheus_fastapi_instrumentator import Instrumentator  # noqa: E402

from api.routers.journal_router import router as journal_router  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

app = FastAPI(title="Journal API", description="A simple journal API for tracking daily work, struggles, and intentions")
app.include_router(journal_router)

# Prometheus metrics — exposes /metrics endpoint automatically
Instrumentator().instrument(app).expose(app)


@app.get("/health")
async def health_check():
    """Health check endpoint for Kubernetes probes and monitoring."""
    import asyncpg

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return JSONResponse(status_code=503, content={"status": "unhealthy", "detail": "DATABASE_URL not configured"})
    try:
        conn = await asyncpg.connect(database_url)
        await conn.execute("SELECT 1")
        await conn.close()
        return {"status": "healthy"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(status_code=503, content={"status": "unhealthy", "detail": str(e)})


logger.info("Journal API started successfully")
