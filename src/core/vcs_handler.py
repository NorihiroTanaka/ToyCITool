import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from git import Repo
from .vcs_utils import inject_auth_token, mask_auth_token

logger = logging.getLogger(__name__)

class IVcsHandler(ABC):
    @abstractmethod
    def __init__(self, workspace_path: str):
        pass

    @abstractmethod
    def prepare_repository(self, url: str, branch: str, access_token: Optional[str] = None) -> None:
        pass
    
    @abstractmethod
    def has_changes(self) -> bool:
        pass

    @abstractmethod
    def commit_and_push(self, message: str, branch: str) -> None:
        pass

    @abstractmethod
    def repo_close(self) -> None:
        pass

class GitHandler(IVcsHandler):
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        self.repo = None

    def prepare_repository(self, url: str, branch: str, access_token: Optional[str] = None) -> None:
        """リポジトリをクローンし、指定ブランチをチェックアウトする"""
        
        # access_token が None の場合の対応を inject_auth_token 側でやってくれることを期待するか、ここで空文字を渡すか
        token_str = access_token if access_token else ""
        auth_url = inject_auth_token(url, token_str)
        
        if access_token:
            masked_url = mask_auth_token(url, access_token)
            logger.info(f"アクセストークンを使用して {masked_url} を {self.workspace_path} にクローンしています...")
        else:
            logger.info(f"{url} を {self.workspace_path} にクローンしています...")

        self.repo = Repo.clone_from(auth_url, self.workspace_path)
        
        # ターゲットブランチをチェックアウト
        if branch in self.repo.heads:
            self.repo.heads[branch].checkout()
        else:
            # check remote branch
            origin = self.repo.remotes.origin
            origin.fetch()
            remote_refs = [ref.name for ref in origin.refs]
            remote_branch_name = f"origin/{branch}"
            
            if remote_branch_name in remote_refs:
                 self.repo.create_head(branch, origin.refs[branch]).set_tracking_branch(origin.refs[branch]).checkout()
            else:
                 self.repo.create_head(branch).checkout()

    def has_changes(self) -> bool:
        """変更があるか確認する"""
        if not self.repo:
            raise Exception("Repository not initialized")
        return self.repo.is_dirty(untracked_files=True)

    def commit_and_push(self, message: str, branch: str) -> None:
        """変更をコミットしてプッシュする"""
        if not self.repo:
            raise Exception("Repository not initialized")
            
        logger.info(f"変更が検出されました。コミット中...")
        self.repo.git.add(A=True)
        
        # Add [skip ci] prefix to the commit message to prevent CI loops
        full_message = f"[skip ci] {message}"
        self.repo.index.commit(full_message)
        
        logger.info(f"{branch} へ変更をプッシュしています...")
        origin = self.repo.remote(name='origin')
        origin.push(branch)
        logger.info(f"プッシュ成功。")

    def repo_close(self) -> None:
        """リポジトリをクローズする (必要ならば)"""
        if self.repo:
            self.repo.close()
            self.repo = None
        