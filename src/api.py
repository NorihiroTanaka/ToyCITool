import asyncio
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .core.logging_config import setup_logging
from .core.container import get_container
from .core.webhook_factory import WebhookProviderFactory
from .core.webhook_handler import verify_github_signature
from .core.exceptions import ToyCIError

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()

    container = get_container()
    app.state.container = container

    logger.info("Application started with configuration loaded.")
    yield

    container.job_service.shutdown(wait=True)
    logger.info("Application shutdown.")

app = FastAPI(lifespan=lifespan)

@app.post("/webhook")
async def webhook(request: Request):
    """Webhookを受け取り、ジョブをキューに追加する"""
    body = await request.body()

    container = request.app.state.container
    webhook_secret = container.settings.server.webhook_secret

    if webhook_secret:
        signature_header = request.headers.get("x-hub-signature-256", "")
        client_host = request.client.host if request.client else "unknown"
        if not verify_github_signature(body, webhook_secret, signature_header):
            logger.warning(f"Webhook署名検証失敗: リモートIP={client_host}")
            return JSONResponse(status_code=403, content={"status": "error", "message": "Invalid signature"})
        logger.info(f"Webhook署名検証成功: リモートIP={client_host}")

    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"JSONペイロードの解析エラー: {e}")
        return {"status": "error", "message": "Invalid JSON payload"}

    provider = WebhookProviderFactory.get_provider(dict(request.headers))
    logger.info(f"プロバイダーを使用: {provider.get_provider_id()}")

    service = container.job_trigger_service

    try:
        loop = asyncio.get_event_loop()
        triggered_jobs = await loop.run_in_executor(
            None, service.process_webhook_event, provider, payload
        )
        return {"status": "ok", "triggered_jobs": triggered_jobs}
    except ToyCIError as e:
        logger.error(f"Webhook処理でエラー: {e}")
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.exception(f"Webhook処理で予期しないエラー: {e}")
        return {"status": "error", "message": "Internal Server Error"}
