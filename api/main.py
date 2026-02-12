
import logging

from dotenv import load_dotenv

load_dotenv(override=True)

from fastapi import FastAPI

from api.routers.journal_router import router as journal_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Journal API", description="A simple journal API for tracking daily work, struggles, and intentions")
app.include_router(journal_router)

logger.info("Journal API started")
