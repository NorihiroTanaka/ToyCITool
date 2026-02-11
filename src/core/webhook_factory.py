from typing import List, Dict
import logging
from .webhook_handler import WebhookProvider, GitHubProvider

logger = logging.getLogger(__name__)

class WebhookProviderFactory:
    _providers: List[WebhookProvider] = [
        GitHubProvider(),
    ]

    @classmethod
    def get_provider(cls, headers: Dict[str, str]) -> WebhookProvider:
        """
        リクエストヘッダーに基づいて適切なプロバイダーを返す。
        マッチしない場合はデフォルト（GitHub）を返す。
        """
        for provider in cls._providers:
            if provider.can_handle(headers):
                return provider
        
        # フォールバック: GitHub
        logger.info("ヘッダーに一致するプロバイダーが見つかりませんでした。GitHubProvider にフォールバックします。")
        return cls._providers[0]
