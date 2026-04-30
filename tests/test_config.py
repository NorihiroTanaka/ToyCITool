"""設定モデルのテスト。"""

import pytest

from src.core.config import GitConfig, JobConfig, Settings


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


class TestJobConfigScripts:
    """JobConfigのscriptsフィールドテスト。"""

    def test_scriptsを設定できる(self):
        config = JobConfig(name="test", scripts=["step1.cmd", "step2.cmd"])
        assert config.scripts == ["step1.cmd", "step2.cmd"]

    def test_scriptsのデフォルトは空リスト(self):
        config = JobConfig(name="test")
        assert config.scripts == []


class TestJobConfigTimeout:
    """JobConfigのtimeoutフィールドテスト。"""

    def test_timeoutのデフォルトはNone(self):
        config = JobConfig(name="test", scripts=["echo hi"])
        assert config.timeout is None

    def test_timeoutを設定できる(self):
        config = JobConfig(name="test", scripts=["echo hi"], timeout=600)
        assert config.timeout == 600


class TestSettingsDefaultTimeout:
    """Settingsのdefault_timeoutフィールドテスト。"""

    def test_default_timeoutのデフォルトは3600(self):
        settings = Settings()
        assert settings.default_timeout == 3600

    def test_default_timeoutを設定できる(self):
        settings = Settings(default_timeout=1800)
        assert settings.default_timeout == 1800
