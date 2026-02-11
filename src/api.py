import logging
import fnmatch
from fastapi import FastAPI, Request, BackgroundTasks
from .core import load_config, run_job
from .core.webhook_handler import WebhookProviderFactory
from .core.job_trigger import JobTriggerService

logger = logging.getLogger(__name__)

app = FastAPI()

@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    """Webhookを受け取り、ジョブをトリガーする"""
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"JSONペイロードの解析エラー: {e}")
        return {"status": "error", "message": "Invalid JSON payload"}

    # Get provider based on headers (fallback to GitHub if not found)
    # request.headers is a Headers object, convert to dict for type safety
    provider = WebhookProviderFactory.get_provider(dict(request.headers))
    logger.info(f"プロバイダーを使用: {provider.get_provider_id()}")
    
    # Use JobTriggerService to handle logic
    service = JobTriggerService(load_config, run_job)
    triggered_jobs = service.process_webhook_event(provider, payload, background_tasks)
            
    return {"status": "ok", "triggered_jobs": triggered_jobs}
