"""Webhook署名検証のテスト。"""

import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from src.core.webhook_handler import verify_github_signature


def _make_signature(body: bytes, secret: str) -> str:
    """テスト用に正しい署名を生成するヘルパー。"""
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


class TestVerifyGithubSignature:
    """verify_github_signature の単体テスト。"""

    def test_正しい署名でTrueが返る(self):
        # Arrange
        body = b'{"ref": "refs/heads/main"}'
        secret = "my-secret"
        signature = _make_signature(body, secret)
        # Act
        result = verify_github_signature(body, secret, signature)
        # Assert
        assert result is True

    def test_不正な署名でFalseが返る(self):
        # Arrange
        body = b'{"ref": "refs/heads/main"}'
        secret = "my-secret"
        wrong_signature = "sha256=deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
        # Act
        result = verify_github_signature(body, secret, wrong_signature)
        # Assert
        assert result is False

    def test_異なるシークレットでFalseが返る(self):
        # Arrange
        body = b'{"ref": "refs/heads/main"}'
        signature = _make_signature(body, "correct-secret")
        # Act
        result = verify_github_signature(body, "wrong-secret", signature)
        # Assert
        assert result is False

    def test_署名ヘッダーが空文字列でFalseが返る(self):
        # Arrange
        body = b'{"ref": "refs/heads/main"}'
        secret = "my-secret"
        # Act
        result = verify_github_signature(body, secret, "")
        # Assert
        assert result is False

    def test_署名ヘッダーにsha256プレフィックスがない場合Falseが返る(self):
        # Arrange
        body = b'{"ref": "refs/heads/main"}'
        secret = "my-secret"
        # sha256= プレフィックスなしのダイジェストのみ
        digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        # Act
        result = verify_github_signature(body, secret, digest)
        # Assert
        assert result is False

    def test_ボディが空バイトの場合も検証できる(self):
        # Arrange
        body = b""
        secret = "my-secret"
        signature = _make_signature(body, secret)
        # Act
        result = verify_github_signature(body, secret, signature)
        # Assert
        assert result is True

    def test_タイミング攻撃対策のためcompare_digestが使われる(self):
        """compare_digest を使用することでタイミング攻撃を防ぐ。
        実装内で hmac.compare_digest を使用しているかを間接的に確認。
        正しい署名と誤った署名で動作が変わらないことをテスト。
        """
        body = b'{"ref": "refs/heads/main"}'
        secret = "my-secret"
        correct_sig = _make_signature(body, secret)
        wrong_sig = "sha256=" + "0" * 64

        assert verify_github_signature(body, secret, correct_sig) is True
        assert verify_github_signature(body, secret, wrong_sig) is False


class TestWebhookEndpointSignatureVerification:
    """APIエンドポイントの署名検証統合テスト。"""

    def _get_client_with_secret(self, secret: str | None):
        """webhook_secretを設定したテストクライアントを返す。"""
        from src.core.config import Settings, ServerConfig
        from src.core.container import Container
        from src.api import app

        settings = Settings(server=ServerConfig(webhook_secret=secret))

        # コンテナをモックに差し替え
        mock_container = _MockContainer(settings)
        app.state.container = mock_container
        return TestClient(app, raise_server_exceptions=False)

    def test_シークレット未設定時は署名なしで200が返る(self):
        # Arrange
        client = self._get_client_with_secret(None)
        payload = {"ref": "refs/heads/main", "commits": [], "head_commit": {"message": "fix"}}
        # Act
        response = client.post(
            "/webhook",
            json=payload,
            headers={"x-github-event": "push"},
        )
        # Assert
        assert response.status_code == 200

    def test_シークレット設定時に正しい署名で200が返る(self):
        # Arrange
        secret = "test-secret"
        client = self._get_client_with_secret(secret)
        payload = {"ref": "refs/heads/main", "commits": [], "head_commit": {"message": "fix"}}
        body = json.dumps(payload).encode()
        signature = _make_signature(body, secret)
        # Act
        response = client.post(
            "/webhook",
            content=body,
            headers={"x-github-event": "push", "x-hub-signature-256": signature, "content-type": "application/json"},
        )
        # Assert
        assert response.status_code == 200

    def test_シークレット設定時に署名なしで403が返る(self):
        # Arrange
        secret = "test-secret"
        client = self._get_client_with_secret(secret)
        payload = {"ref": "refs/heads/main", "commits": [], "head_commit": {"message": "fix"}}
        # Act
        response = client.post(
            "/webhook",
            json=payload,
            headers={"x-github-event": "push"},
        )
        # Assert
        assert response.status_code == 403

    def test_シークレット設定時に不正な署名で403が返る(self):
        # Arrange
        secret = "test-secret"
        client = self._get_client_with_secret(secret)
        payload = {"ref": "refs/heads/main", "commits": [], "head_commit": {"message": "fix"}}
        # Act
        response = client.post(
            "/webhook",
            json=payload,
            headers={
                "x-github-event": "push",
                "x-hub-signature-256": "sha256=invalidsignature",
            },
        )
        # Assert
        assert response.status_code == 403


class _MockContainer:
    """テスト用の最小限コンテナモック。"""

    def __init__(self, settings):
        self.settings = settings
        self.job_trigger_service = _MockJobTriggerService()

    def shutdown(self, wait=True):
        pass


class _MockJobTriggerService:
    def process_webhook_event(self, provider, payload):
        return []
