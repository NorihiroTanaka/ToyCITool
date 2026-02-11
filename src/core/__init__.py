import logging
from typing import Dict, Any, Optional, Type

from .workspace_manager import WorkspaceManager
from .vcs_handler import GitHandler
from .job_executor import ShellJobExecutor
from .job_service import JobService
from .interfaces import IVcsHandler, IJobExecutor
from .container import get_container

# ロガーの設定 (必要に応じて親モジュールで設定することを推奨)
logger = logging.getLogger(__name__)

def run_job(
    job: Dict[str, Any],
    commit_info: Dict[str, Any],
    workspace_manager: Optional[WorkspaceManager] = None,
    vcs_handler_cls: Type[IVcsHandler] = GitHandler,
    job_executor_cls: Type[IJobExecutor] = ShellJobExecutor
) -> None:
    """
    CIジョブを実行する一連のフローを制御します。
    DEPRECATED: JobService.run_job を直接使用してください。

    Args:
        job (Dict[str, Any]): ジョブの設定情報 (name, repo_url, target_branch, script)。
        commit_info (Dict[str, Any]): トリガーとなったコミット情報 (id, modified)。
        workspace_manager (Optional[WorkspaceManager]): ワークスペース管理クラスのインスタンス。指定がない場合はデフォルトを使用。
        vcs_handler_cls (Type[IVcsHandler]): VCS操作クラス。デフォルトは GitHandler。
        job_executor_cls (Type[IJobExecutor]): ジョブ実行クラス。デフォルトは ShellJobExecutor。
    """
    # 互換性維持のため、ContainerからデフォルトのSettingsを取得して渡す
    container = get_container()
    service = JobService(container.settings, workspace_manager, vcs_handler_cls, job_executor_cls)
    service.run_job(job, commit_info)
