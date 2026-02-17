"""カスタム例外クラスのテスト。"""

import pytest

from src.core.exceptions import (
    ToyCIError,
    ScriptExecutionError,
    RepositoryError,
    RepositoryNotInitializedError,
    WorkspaceError,
    WorkspaceCleanupError,
    JobValidationError,
    WebhookPayloadError,
)


class TestExceptionHierarchy:
    """例外の継承階層が正しいことを検証する。"""

    @pytest.mark.parametrize(
        "exc_cls",
        [
            ScriptExecutionError,
            RepositoryError,
            RepositoryNotInitializedError,
            WorkspaceError,
            WorkspaceCleanupError,
            JobValidationError,
            WebhookPayloadError,
        ],
    )
    def test_全てのカスタム例外はToyCIErrorを継承する(self, exc_cls):
        assert issubclass(exc_cls, ToyCIError)

    def test_RepositoryNotInitializedErrorはRepositoryErrorを継承する(self):
        assert issubclass(RepositoryNotInitializedError, RepositoryError)

    def test_WorkspaceCleanupErrorはWorkspaceErrorを継承する(self):
        assert issubclass(WorkspaceCleanupError, WorkspaceError)

    def test_全てのカスタム例外はExceptionを継承する(self):
        assert issubclass(ToyCIError, Exception)

    def test_exceptToyCIErrorで全てのカスタム例外を捕捉できる(self):
        exceptions = [
            ScriptExecutionError("test"),
            RepositoryError("test"),
            RepositoryNotInitializedError("test"),
            WorkspaceError("test"),
            WorkspaceCleanupError("test"),
            JobValidationError("test"),
            WebhookPayloadError("test"),
        ]
        for exc in exceptions:
            with pytest.raises(ToyCIError):
                raise exc


class TestScriptExecutionError:
    """ScriptExecutionErrorの属性テスト。"""

    def test_デフォルト属性値(self):
        exc = ScriptExecutionError("スクリプトが失敗しました")
        assert str(exc) == "スクリプトが失敗しました"
        assert exc.stdout == ""
        assert exc.stderr == ""
        assert exc.return_code == -1

    def test_カスタム属性値(self):
        exc = ScriptExecutionError(
            "エラー",
            stdout="output",
            stderr="error output",
            return_code=1,
        )
        assert str(exc) == "エラー"
        assert exc.stdout == "output"
        assert exc.stderr == "error output"
        assert exc.return_code == 1

    def test_メッセージがstrで取得できる(self):
        exc = ScriptExecutionError("テストメッセージ")
        assert str(exc) == "テストメッセージ"
