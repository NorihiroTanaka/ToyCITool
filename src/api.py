import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, BackgroundTasks

from .core.logging_config import setup_logging
from .core.container import get_container
from .core.webhook_factory import WebhookProviderFactory
from .core.exceptions import ToyCIError

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()

    container = get_container()
    app.state.container = container

    logger.info("Application started with configuration loaded.")
    yield
    logger.info("Application shutdown.")

app = FastAPI(lifespan=lifespan)

@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    """Webhookを受け取り、ジョブをトリガーする"""
    try:
        payload = await request.json()
    except (json.JSONDecodeError, ValueError) as e:
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
    except ToyCIError as e:
        logger.error(f"Webhook処理でエラー: {e}")
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.exception(f"Webhook処理で予期しないエラー: {e}")
        return {"status": "error", "message": "Internal Server Error"}
