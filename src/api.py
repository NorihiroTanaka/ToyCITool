import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, BackgroundTasks
from .core.logging_config import setup_logging

from .core.container import get_container
from .core.webhook_factory import WebhookProviderFactory

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load logging configuration
    setup_logging()
    
    # Initialize container
    container = get_container()
    app.state.container = container
    
    logger.info("Application started with configuration loaded.")
    yield
    logger.info("Application shutdown.")

logger = logging.getLogger(__name__)
app = FastAPI(lifespan=lifespan)

@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    """Webhookを受け取り、ジョブをトリガーする"""
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"JSONペイロードの解析エラー: {e}")
        return {"status": "error", "message": "Invalid JSON payload"}

    # Get provider based on headers (fallback to GitHub if not found)
    provider = WebhookProviderFactory.get_provider(dict(request.headers))
    logger.info(f"プロバイダーを使用: {provider.get_provider_id()}")
    
    # Use JobTriggerService from container to handle logic
    container = request.app.state.container
    service = container.job_trigger_service
    
    try:
        triggered_jobs = service.process_webhook_event(provider, payload, background_tasks)
        return {"status": "ok", "triggered_jobs": triggered_jobs}
    except Exception as e:
        logger.exception(f"Webhook processing failed: {e}")
        return {"status": "error", "message": "Internal Server Error"}
