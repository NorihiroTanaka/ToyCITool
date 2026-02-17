"""GitHandlerのテスト。"""

from unittest.mock import patch, MagicMock

import pytest

from src.core.vcs_handler import GitHandler
from src.core.exceptions import RepositoryNotInitializedError


class TestGitHandlerNotInitialized:
    """リポジトリ未初期化時のエラーテスト。"""

    def setup_method(self):
        self.handler = GitHandler("/tmp/workspace")

    def test_has_changesでRepositoryNotInitializedErrorが発生する(self):
        assert self.handler.repo is None
        with pytest.raises(RepositoryNotInitializedError):
            self.handler.has_changes()

    def test_commit_and_pushでRepositoryNotInitializedErrorが発生する(self):
        assert self.handler.repo is None
        with pytest.raises(RepositoryNotInitializedError):
            self.handler.commit_and_push("test message", "main")


class TestGitHandlerContextManager:
    """コンテキストマネージャのテスト。"""

    def test_withブロックで使用できる(self):
        with GitHandler("/tmp/workspace") as handler:
            assert isinstance(handler, GitHandler)

    def test_withブロックを抜けた後にcloseが呼ばれる(self):
        handler = GitHandler("/tmp/workspace")
        mock_repo = MagicMock()
        handler.repo = mock_repo

        with handler:
            pass

        # close() により repo が None になるが、元のモックで検証
        mock_repo.close.assert_called_once()

    def test_例外発生時もcloseが呼ばれる(self):
        handler = GitHandler("/tmp/workspace")
        mock_repo = MagicMock()
        handler.repo = mock_repo

        with pytest.raises(ValueError):
            with handler:
                raise ValueError("test error")

        mock_repo.close.assert_called_once()


class TestGitHandlerClose:
    """close メソッドのテスト。"""

    def test_repoがNoneでもエラーにならない(self):
        handler = GitHandler("/tmp/workspace")
        handler.close()  # 例外が発生しないこと

    def test_close後にrepoがNoneになる(self):
        handler = GitHandler("/tmp/workspace")
        handler.repo = MagicMock()
        handler.close()
        assert handler.repo is None
