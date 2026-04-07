from typing import Dict, Any, Optional, Type, List, Tuple
import logging
import uuid
import queue
import threading

from .config import Settings
from .workspace_manager import WorkspaceManager
from .vcs_handler import GitHandler
from .job_executor import ShellJobExecutor
from .interfaces import IJobService, IVcsHandler, IJobExecutor
from .exceptions import ToyCIError, JobValidationError
from .notifier import Notifier, NotificationEvent, build_notifier

logger = logging.getLogger(__name__)

_JOB_QUEUE_SENTINEL = None
"""ワーカー停止を通知するセンチネル値。"""


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

        notifications_raw = (
            settings.notifications.model_dump() if settings.notifications else None
        )
        self._notifier: Notifier = build_notifier(notifications_raw)

        self._job_queue: queue.Queue[Optional[Tuple[Dict[str, Any], Dict[str, Any]]]] = queue.Queue()
        self._workers: List[threading.Thread] = []
        self._start_workers()

    # ------------------------------------------------------------------
    # Worker management
    # ------------------------------------------------------------------

    def _start_workers(self) -> None:
        max_workers = self.settings.max_concurrent_jobs
        logger.info(f"ジョブワーカーを {max_workers} 個起動します。")
        for i in range(max_workers):
            t = threading.Thread(
                target=self._worker_loop,
                name=f"JobWorker-{i + 1}",
                daemon=True,
            )
            t.start()
            self._workers.append(t)

    def _worker_loop(self) -> None:
        while True:
            item = self._job_queue.get()
            if item is _JOB_QUEUE_SENTINEL:
                self._job_queue.task_done()
                break
            job_config, commit_info = item
            try:
                self.run_job(job_config, commit_info)
            finally:
                self._job_queue.task_done()

    def submit_job(self, job_config: Dict[str, Any], commit_info: Dict[str, Any]) -> None:
        """ジョブをキューに追加する。"""
        job_name = job_config.get("name", "unknown")
        queue_size = self._job_queue.qsize()
        logger.info(
            f"[{job_name}] ジョブをキューに追加しました。"
            f" (待機中のジョブ数: {queue_size})"
        )
        self._job_queue.put((job_config, commit_info))

    def shutdown(self, wait: bool = True) -> None:
        """ワーカースレッドを停止する。"""
        logger.info("ジョブサービスをシャットダウンしています...")
        for _ in self._workers:
            self._job_queue.put(_JOB_QUEUE_SENTINEL)
        if wait:
            for w in self._workers:
                w.join()
        logger.info("ジョブサービスのシャットダウンが完了しました。")

    # ------------------------------------------------------------------
    # Job execution
    # ------------------------------------------------------------------

    def run_job(self, job_config: Dict[str, Any], commit_info: Dict[str, Any]) -> None:
        """
        CIジョブを実行する一連のフローを制御します。

        Args:
            job_config (Dict[str, Any]): ジョブの設定情報 (name, repo_url, target_branch, script)。
            commit_info (Dict[str, Any]): トリガーとなったコミット情報 (id, modified)。
        """
        job_name = job_config.get("name", "unknown_job")

        repo_url = job_config.get("repo_url") or self.settings.git.repo_url
        target_branch = job_config.get("target_branch")
        script = job_config.get("script")

        if not repo_url or not target_branch or not script:
            raise JobValidationError(
                f"[{job_name}] repo_url, target_branch, script は必須です。"
                f" repo_url={repo_url}, target_branch={target_branch}, script={script}"
            )

        repo_url_str: str = str(repo_url)
        target_branch_str: str = str(target_branch)
        script_str: str = str(script)

        user_env: Dict[str, str] = job_config.get("env", {})
        venv_path: Optional[str] = job_config.get("venv")

        job_timeout = job_config.get("timeout")
        effective_timeout = job_timeout if job_timeout is not None else self.settings.default_timeout

        error_message: Optional[str] = None
        success = False
        try:
            with self.workspace_manager.workspace_lock(job_name):
                work_dir = self._prepare_workspace(job_name)
                try:
                    ci_env = self._build_ci_env(
                        job_name=job_name,
                        commit_info=commit_info,
                        repo_url=repo_url_str,
                        branch=target_branch_str,
                        workspace=work_dir,
                    )
                    env = {**user_env, **ci_env}

                    with self._checkout_code(job_name, work_dir, repo_url_str, target_branch_str) as vcs_handler:
                        self._execute_script(job_name, work_dir, script_str, env, timeout_seconds=effective_timeout, venv=venv_path)
                        self._handle_result(job_name, vcs_handler, commit_info, target_branch_str)
                finally:
                    self._cleanup_workspace(job_name)

            success = True

        except ToyCIError as e:
            error_message = str(e)
            logger.exception(f"[{job_name}] ジョブが失敗しました: {e}")
        except Exception as e:
            error_message = str(e)
            logger.exception(f"[{job_name}] 予期しないエラーが発生しました: {e}")
        finally:
            self._send_notification(
                job_name=job_name,
                commit_info=commit_info,
                branch=target_branch_str,
                success=success,
                error_message=error_message,
            )

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

    def _execute_script(self, job_name: str, work_dir: str, script: str, env: Optional[Dict[str, str]] = None, timeout_seconds: Optional[int] = None, venv: Optional[str] = None) -> None:
        logger.info(f"[{job_name}] スクリプトを実行中: {script}")
        executor = self.job_executor_cls(self.settings.job_log_dir)
        executor.execute(script, work_dir, job_name=job_name, env=env, timeout_seconds=timeout_seconds, venv=venv)

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

    def _send_notification(
        self,
        job_name: str,
        commit_info: Dict[str, Any],
        branch: str,
        success: bool,
        error_message: Optional[str] = None,
    ) -> None:
        event = NotificationEvent(
            job_name=job_name,
            success=success,
            branch=branch,
            commit_hash=str(commit_info.get("id", "")),
            commit_message=commit_info.get("message"),
            error_message=error_message,
        )
        try:
            self._notifier.notify(event)
        except Exception as e:
            logger.warning(f"[{job_name}] 通知の送信中にエラーが発生しました: {e}")
