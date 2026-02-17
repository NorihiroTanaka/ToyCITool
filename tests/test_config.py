"""設定モデルのテスト。"""

import pytest

from src.core.config import GitConfig, Settings


class TestGitConfig:
    """GitConfigの命名規約テスト。"""

    def test_access_tokenでインスタンス構築できる(self):
        config = GitConfig(access_token="my_token")
        assert config.access_token == "my_token"

    def test_accessTokenエイリアスでインスタンス構築できる(self):
        """既存のconfig.yaml（accessTokenキー）との後方互換性。"""
        config = GitConfig(accessToken="my_token")
        assert config.access_token == "my_token"

    def test_access_tokenのデフォルトはNone(self):
        config = GitConfig()
        assert config.access_token is None

    def test_repo_urlも正常に動作する(self):
        config = GitConfig(access_token="token", repo_url="https://example.com/repo.git")
        assert config.repo_url == "https://example.com/repo.git"
        assert config.access_token == "token"
