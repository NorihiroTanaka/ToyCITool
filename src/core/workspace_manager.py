import os
import stat
import shutil
import time
import logging

from .exceptions import WorkspaceError, WorkspaceCleanupError

logger = logging.getLogger(__name__)

_MAX_CLEANUP_RETRIES: int = 3
"""ワークスペース削除のリトライ最大回数。"""

_CLEANUP_RETRY_DELAY_SEC: float = 1.0
"""ワークスペース削除リトライ時の待機秒数。"""


class WorkspaceManager:
    def __init__(self, base_dir: str = "./workspace"):
        self.base_dir = os.path.abspath(base_dir)

    def remove_readonly(self, func, path, _):
        """読み取り専用ファイルを削除するためのヘルパー関数"""
        os.chmod(path, stat.S_IWRITE)
        func(path)

    def prepare_workspace(self, job_name: str) -> str:
        """ワークスペースを準備する (既存なら削除して作成)"""
        work_dir = os.path.join(self.base_dir, job_name)
        
        if os.path.exists(work_dir):
            try:
                shutil.rmtree(work_dir, onexc=self.remove_readonly)
            except Exception as e:
                raise WorkspaceError(f"ワークスペースの初期化に失敗しました: {e}") from e
                
        os.makedirs(work_dir, exist_ok=True)
        return work_dir

    def cleanup_workspace(self, job_name: str):
        """ワークスペースを削除する"""
        work_dir = os.path.join(self.base_dir, job_name)
        
        if os.path.exists(work_dir):
            for i in range(_MAX_CLEANUP_RETRIES):
                try:
                    shutil.rmtree(work_dir, onexc=self.remove_readonly)
                    logger.info(f"ワークスペース {work_dir} を削除しました。")
                    return
                except Exception as e:
                    logger.warning(f"ワークスペースの削除に失敗しました (試行 {i+1}/{_MAX_CLEANUP_RETRIES}): {e}")
                    time.sleep(_CLEANUP_RETRY_DELAY_SEC)
            
            logger.error(f"ワークスペース {work_dir} の削除に最終的に失敗しました。")
            raise WorkspaceCleanupError(f"ワークスペースの削除にリトライ後も失敗しました: {work_dir}")