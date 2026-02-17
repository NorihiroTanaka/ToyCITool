from typing import Dict, Any, Optional, Type
import logging
import uuid

from .config import Settings
from .workspace_manager import WorkspaceManager
from .vcs_handler import GitHandler
from .job_executor import ShellJobExecutor
from .interfaces import IJobService, IVcsHandler, IJobExecutor
from .exceptions import ToyCIError, JobValidationError

logger = logging.getLogger(__name__)

class JobService(IJobService):
    def __init__(
        self,
        settings: Settings,
        workspace_manager: Optional[WorkspaceManager] = None,
        vcs_handler_cls: Type[IVcsHandler] = GitHandler,
        job_executor_cls: Type[IJobExecutor] = ShellJobExecutor
    ):
        self.settings = settings
        self.workspace_manager = workspace_manager or WorkspaceManager()
        self.vcs_handler_cls = vcs_handler_cls
        self.job_executor_cls = job_executor_cls

    def run_job(self, job_config: Dict[str, Any], commit_info: Dict[str, Any]) -> None:
        """
        CIジョブを実行する一連のフローを制御します。

        Args:
            job_config (Dict[str, Any]): ジョブの設定情報 (name, repo_url, target_branch, script)。
            commit_info (Dict[str, Any]): トリガーとなったコミット情報 (id, modified)。
        """
        # settingsからデフォルト値を補完しつつ、job_configを使用する
        job_name = job_config.get("name", "unknown_job")
        
        # job_configになければ、settings.git.repo_url を使うフォールバックロジックも検討可能だが、
        # job定義には必須項目として扱うのが自然。ただし、GitConfig全体設定があるならそれを使うのもあり。
        repo_url = job_config.get("repo_url") or self.settings.git.repo_url
        target_branch = job_config.get("target_branch")
        script = job_config.get("script")
        
        if not repo_url or not target_branch or not script:
            raise JobValidationError(
                f"[{job_name}] repo_url, target_branch, script は必須です。"
                f" repo_url={repo_url}, target_branch={target_branch}, script={script}"
            )

        # Pylance/MyPy type narrowing
        repo_url_str: str = str(repo_url)
        target_branch_str: str = str(target_branch)
        script_str: str = str(script)

        # ユーザー定義の環境変数
        user_env: Dict[str, str] = job_config.get("env", {})

        try:
            work_dir = self._prepare_workspace(job_name)
            try:
                ci_env = self._build_ci_env(
                    job_name=job_name,
                    commit_info=commit_info,
                    repo_url=repo_url_str,
                    branch=target_branch_str,
                    workspace=work_dir,
                )
                # ユーザー定義 → CI メタデータの順でマージ（CI 変数が優先）
                env = {**user_env, **ci_env}

                with self._checkout_code(job_name, work_dir, repo_url_str, target_branch_str) as vcs_handler:
                    self._execute_script(job_name, work_dir, script_str, env)
                    self._handle_result(job_name, vcs_handler, commit_info, target_branch_str)
            finally:
                self._cleanup_workspace(job_name)

        except ToyCIError as e:
            logger.exception(f"[{job_name}] ジョブが失敗しました: {e}")
        except Exception as e:
            logger.exception(f"[{job_name}] 予期しないエラーが発生しました: {e}")

    def _prepare_workspace(self, job_name: str) -> str:
        logger.info(f"[{job_name}] ワークスペースを準備中...")
        try:
            return self.workspace_manager.prepare_workspace(job_name)
        except Exception as e:
            logger.exception(f"[{job_name}] ワークスペースの準備に失敗しました: {e}")
            raise

    def _checkout_code(self, job_name: str, work_dir: str, repo_url: str, target_branch: str) -> IVcsHandler:
        access_token = self.settings.git.access_token
        
        vcs_handler = self.vcs_handler_cls(work_dir)
        logger.info(f"[{job_name}] リポジトリを準備中: {repo_url} ({target_branch})")
        vcs_handler.prepare_repository(repo_url, target_branch, access_token)
        return vcs_handler

    def _build_ci_env(
        self,
        job_name: str,
        commit_info: Dict[str, Any],
        repo_url: str,
        branch: str,
        workspace: str,
    ) -> Dict[str, str]:
        """CI メタデータ環境変数を構築する"""
        return {
            "CI_JOB_ID": f"{job_name}-{uuid.uuid4().hex[:8]}",
            "CI_COMMIT_HASH": str(commit_info.get("id", "")),
            "CI_BRANCH": branch,
            "CI_REPO_URL": repo_url,
            "CI_WORKSPACE": workspace,
        }

    def _execute_script(self, job_name: str, work_dir: str, script: str, env: Optional[Dict[str, str]] = None) -> None:
        logger.info(f"[{job_name}] スクリプトを実行中: {script}")
        executor = self.job_executor_cls()
        executor.execute(script, work_dir, job_name=job_name, env=env)

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
