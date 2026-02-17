"""vcs_utils の純粋関数テスト。"""

import pytest

from src.core.vcs_utils import inject_auth_token, mask_auth_token


class TestInjectAuthToken:
    """inject_auth_token のテスト。"""

    def test_HTTPSのURLにトークンが埋め込まれる(self):
        url = "https://github.com/example/repo.git"
        result = inject_auth_token(url, "my_token")
        assert result == "https://my_token@github.com/example/repo.git"

    def test_HTTPのURLにトークンが埋め込まれる(self):
        url = "http://github.com/example/repo.git"
        result = inject_auth_token(url, "my_token")
        assert result == "http://my_token@github.com/example/repo.git"

    def test_ポート付きURLでも正しく動作する(self):
        url = "https://git.example.com:8443/repo.git"
        result = inject_auth_token(url, "token123")
        assert result == "https://token123@git.example.com:8443/repo.git"

    def test_トークンが空文字の場合に元URLがそのまま返る(self):
        url = "https://github.com/example/repo.git"
        result = inject_auth_token(url, "")
        assert result == url

    def test_SSHのURLではトークンが無視される(self):
        url = "git@github.com:example/repo.git"
        result = inject_auth_token(url, "my_token")
        assert result == url


class TestMaskAuthToken:
    """mask_auth_token のテスト。"""

    def test_トークンがマスクされる(self):
        url = "https://my_token@github.com/example/repo.git"
        result = mask_auth_token(url, "my_token")
        assert "my_token" not in result
        assert "*****" in result

    def test_トークンが空の場合に元URLがそのまま返る(self):
        url = "https://github.com/example/repo.git"
        result = mask_auth_token(url, "")
        assert result == url

    def test_トークンがURL中に存在しない場合もエラーにならない(self):
        url = "https://github.com/example/repo.git"
        result = mask_auth_token(url, "nonexistent_token")
        assert result == url
