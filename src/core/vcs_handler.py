import logging
from typing import Any, Optional

from git import Repo

from .interfaces import IVcsHandler
from .vcs_utils import inject_auth_token, mask_auth_token
from .exceptions import RepositoryNotInitializedError

logger = logging.getLogger(__name__)


class GitHandler(IVcsHandler):
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        self.repo = None
        self.access_token: Optional[str] = None
        self.original_url: Optional[str] = None

    def prepare_repository(self, url: str, branch: str, access_token: Optional[str] = None) -> None:
        """リポジトリをクローンし、指定ブランチをチェックアウトする。"""
        self._store_credentials(url, access_token)
        self._clone_repository(url, access_token)
        self._set_authenticated_remote_url()
        self._checkout_branch(branch)

    def has_changes(self) -> bool:
        """変更があるか確認する。"""
        if not self.repo:
            raise RepositoryNotInitializedError("リポジトリが初期化されていません")
        return self.repo.is_dirty(untracked_files=True)

    def commit_and_push(self, message: str, branch: str) -> None:
        """変更をコミットしてプッシュする。"""
        if not self.repo:
            raise RepositoryNotInitializedError("リポジトリが初期化されていません")

        logger.info("変更が検出されました。コミット中...")
        self.repo.git.add(A=True)

        full_message = f"[skip ci] {message}"
        self.repo.index.commit(full_message)

        self._set_authenticated_remote_url()

        logger.info(f"{branch} へ変更をプッシュしています...")
        origin = self.repo.remote(name='origin')
        origin.push(branch)
        logger.info("プッシュ成功。")

    def close(self) -> None:
        """リポジトリをクローズする。"""
        if self.repo:
            self.repo.close()
            self.repo = None

    def __enter__(self) -> "GitHandler":
        """コンテキストマネージャのエントリー。"""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """コンテキストマネージャのクリーンアップ。"""
        self.close()

    # --- プライベートメソッド ---

    def _store_credentials(self, url: str, access_token: Optional[str]) -> None:
        """認証情報を保存する（push時に使用）。"""
        self.access_token = access_token
        self.original_url = url

    def _clone_repository(self, url: str, access_token: Optional[str]) -> None:
        """リポジトリをクローンする。"""
        token_str = access_token if access_token else ""
        auth_url = inject_auth_token(url, token_str)

        if access_token:
            masked_url = mask_auth_token(url, access_token)
            logger.info(f"アクセストークンを使用して {masked_url} を {self.workspace_path} にクローンしています...")
        else:
            logger.info(f"{url} を {self.workspace_path} にクローンしています...")

        self.repo = Repo.clone_from(auth_url, self.workspace_path)

    def _set_authenticated_remote_url(self) -> None:
        """認証トークン付きURLをリモートoriginに設定する。"""
        if self.access_token and self.original_url and self.repo:
            auth_url = inject_auth_token(self.original_url, self.access_token)
            origin = self.repo.remote(name='origin')
            origin.set_url(auth_url)
            logger.debug("Remote URLを認証付きURLに設定しました")

    def _checkout_branch(self, branch: str) -> None:
        """指定ブランチをチェックアウトする。"""
        if branch in self.repo.heads:
            self.repo.heads[branch].checkout()
        else:
            origin = self.repo.remotes.origin
            origin.fetch()
            remote_refs = [ref.name for ref in origin.refs]
            remote_branch_name = f"origin/{branch}"

            if remote_branch_name in remote_refs:
                self.repo.create_head(
                    branch, origin.refs[branch]
                ).set_tracking_branch(origin.refs[branch]).checkout()
            else:
                self.repo.create_head(branch).checkout()
