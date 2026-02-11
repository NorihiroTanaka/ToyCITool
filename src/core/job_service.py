from typing import Dict, Any, Optional, Type
import logging
from .config_loader import load_config
from .workspace_manager import WorkspaceManager
from .vcs_handler import GitHandler, IVcsHandler
from .job_executor import ShellJobExecutor, IJobExecutor

logger = logging.getLogger(__name__)

class JobService:
    def __init__(
        self,
        workspace_manager: Optional[WorkspaceManager] = None,
        vcs_handler_cls: Type[IVcsHandler] = GitHandler,
        job_executor_cls: Type[IJobExecutor] = ShellJobExecutor
    ):
        self.workspace_manager = workspace_manager or WorkspaceManager()
        self.vcs_handler_cls = vcs_handler_cls
        self.job_executor_cls = job_executor_cls
        
        # 全体設定の読み込み (アクセストークン取得のため)
        # TODO: これもDIするか、Service初期化時に渡すようにするとより良い
        self.config = load_config()

    def run_job(self, job: Dict[str, Any], commit_info: Dict[str, Any]) -> None:
        """
        CIジョブを実行する一連のフローを制御します。

        Args:
            job (Dict[str, Any]): ジョブの設定情報 (name, repo_url, target_branch, script)。
            commit_info (Dict[str, Any]): トリガーとなったコミット情報 (id, modified)。
        """
        job_name = job.get("name", "unknown_job")
        repo_url = job.get("repo_url")
        target_branch = job.get("target_branch")
        script = job.get("script")
        
        # Pylance対応: 型チェックと変数の再定義
        if not repo_url or not target_branch or not script:
             logger.error(f"[{job_name}] 設定が無効です: repo_url, target_branch, script は必須です。")
             return

        # ここで型が str であることは保証される
        repo_url_str: str = repo_url
        target_branch_str: str = target_branch
        script_str: str = script

        try:
            # 1. Workspace Preparation
            work_dir = self._prepare_workspace(job_name)
            
            # 2. VCS Operations & 3. Job Execution & 4. Result Handling
            # work_dir が必要なので、これらのステップは try ブロック内で実行
            try:
                vcs_handler = self._checkout_code(job_name, work_dir, repo_url_str, target_branch_str)
                self._execute_script(job_name, work_dir, script_str)
                self._handle_result(job_name, vcs_handler, commit_info, target_branch_str)
            finally:
                # 5. Cleanup Workspace (エラーがあっても必ず実行)
                self._cleanup_workspace(job_name)

        except Exception as e:
            logger.exception(f"[{job_name}] ジョブが失敗しました: {e}")

    def _prepare_workspace(self, job_name: str) -> str:
        logger.info(f"[{job_name}] ワークスペースを準備中...")
        try:
            return self.workspace_manager.prepare_workspace(job_name)
        except Exception as e:
            logger.exception(f"[{job_name}] ワークスペースの準備に失敗しました: {e}")
            raise

    def _checkout_code(self, job_name: str, work_dir: str, repo_url: str, target_branch: str) -> IVcsHandler:
        git_config = self.config.get("git", {})
        access_token = git_config.get("accessToken")
        
        vcs_handler = self.vcs_handler_cls(work_dir)
        logger.info(f"[{job_name}] リポジトリを準備中: {repo_url} ({target_branch})")
        vcs_handler.prepare_repository(repo_url, target_branch, access_token)
        return vcs_handler

    def _execute_script(self, job_name: str, work_dir: str, script: str) -> None:
        logger.info(f"[{job_name}] スクリプトを実行中: {script}")
        executor = self.job_executor_cls()
        executor.execute(script, work_dir)

    def _handle_result(self, job_name: str, vcs_handler: IVcsHandler, commit_info: Dict[str, Any], target_branch: str) -> None:
        if vcs_handler.has_changes():
            commit_id = commit_info.get('id', 'unknown')
            modified_files = ', '.join(commit_info.get('modified', []))
            commit_message = f"CIツールによる自動生成コミット ({commit_id})\n\n変更トリガー: {modified_files}"
            
            logger.info(f"[{job_name}] 変更が検出されました。{target_branch} へプッシュします...")
            vcs_handler.commit_and_push(commit_message, target_branch)
            logger.info(f"[{job_name}] プッシュ成功。")
        else:
            logger.info(f"[{job_name}] 変更は検出されませんでした。")

    def _cleanup_workspace(self, job_name: str) -> None:
        self.workspace_manager.cleanup_workspace(job_name)
