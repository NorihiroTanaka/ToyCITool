"""ToyCIToolのカスタム例外定義モジュール。

全てのカスタム例外はToyCIErrorを基底クラスとし、
モジュールごとに適切な例外クラスを使い分ける。
"""


class ToyCIError(Exception):
    """ToyCITool全体の基底例外クラス。"""
    pass


class ScriptExecutionError(ToyCIError):
    """スクリプト実行時のエラー。

    Attributes:
        stdout: 標準出力の内容
        stderr: 標準エラー出力の内容
        return_code: プロセスの終了コード
    """

    def __init__(
        self,
        message: str,
        stdout: str = "",
        stderr: str = "",
        return_code: int = -1,
    ) -> None:
        super().__init__(message)
        self.stdout = stdout
        self.stderr = stderr
        self.return_code = return_code


class RepositoryError(ToyCIError):
    """VCS操作に関するエラー。"""
    pass


class RepositoryNotInitializedError(RepositoryError):
    """リポジトリが初期化されていない状態でのアクセスエラー。"""
    pass


class WorkspaceError(ToyCIError):
    """ワークスペース操作に関するエラー。"""
    pass


class WorkspaceCleanupError(WorkspaceError):
    """ワークスペース削除失敗時のエラー。"""
    pass


class JobValidationError(ToyCIError):
    """ジョブ設定のバリデーションエラー。"""
    pass


class WebhookPayloadError(ToyCIError):
    """Webhookペイロードの解析エラー。"""
    pass
