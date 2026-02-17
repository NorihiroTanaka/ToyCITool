"""WebhookProviderFactory のテスト。"""

import pytest

from src.core.webhook_factory import WebhookProviderFactory
from src.core.webhook_handler import GitHubProvider


class TestWebhookProviderFactory:
    def test_GitHubヘッダがある場合にGitHubProviderが返る(self, mock_github_headers):
        provider = WebhookProviderFactory.get_provider(mock_github_headers)
        assert isinstance(provider, GitHubProvider)

    def test_未知のヘッダの場合にGitHubProviderにフォールバックする(self):
        headers = {"x-unknown-event": "push"}
        provider = WebhookProviderFactory.get_provider(headers)
        assert isinstance(provider, GitHubProvider)

    def test_空ヘッダの場合にGitHubProviderにフォールバックする(self):
        provider = WebhookProviderFactory.get_provider({})
        assert isinstance(provider, GitHubProvider)
