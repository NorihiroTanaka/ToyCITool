import logging
from typing import Dict, Any, Optional, Type

from .config_loader import load_config, ConfigLoader
from .workspace_manager import WorkspaceManager
from .vcs_handler import GitHandler, IVcsHandler
from .job_executor import ShellJobExecutor, IJobExecutor

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

    Args:
        job (Dict[str, Any]): ジョブの設定情報 (name, repo_url, target_branch, script)。
        commit_info (Dict[str, Any]): トリガーとなったコミット情報 (id, modified)。
        workspace_manager (Optional[WorkspaceManager]): ワークスペース管理クラスのインスタンス。指定がない場合はデフォルトを使用。
        vcs_handler_cls (Type[IVcsHandler]): VCS操作クラス。デフォルトは GitHandler。
        job_executor_cls (Type[IJobExecutor]): ジョブ実行クラス。デフォルトは ShellJobExecutor。
    """
    job_name = job.get("name", "unknown_job")
    repo_url = job.get("repo_url")
    target_branch = job.get("target_branch")
    script = job.get("script")
    
    if not repo_url or not script or not target_branch:
        logger.error(f"[{job_name}] 設定が無効です: repo_url, target_branch, script は必須です。")
        return

    # 全体設定の読み込み (アクセストークン取得のため)
    config = load_config()
    git_config = config.get("git", {})
    access_token = git_config.get("accessToken")

    # 依存関係の初期化 (DIされていない場合)
    if workspace_manager is None:
        workspace_manager = WorkspaceManager()

    # 1. Workspace Preparation
    try:
        logger.info(f"[{job_name}] ワークスペースを準備中...")
        work_dir = workspace_manager.prepare_workspace(job_name)
    except Exception as e:
        logger.exception(f"[{job_name}] ワークスペースの準備に失敗しました: {e}")
        return

    try:
        # 2. VCS Operations
        # work_dir は動的に決まるため、クラスではなくインスタンス化はここで行う必要がある
        # (DIでインスタンスを渡す場合はFactoryパターンなどが必要だが、ここではクラスを渡す形にする)
        vcs_handler = vcs_handler_cls(work_dir)
        logger.info(f"[{job_name}] リポジトリを準備中: {repo_url} ({target_branch})")
        vcs_handler.prepare_repository(repo_url, target_branch, access_token)

        # 3. Job Execution
        logger.info(f"[{job_name}] スクリプトを実行中: {script}")
        executor = job_executor_cls()
        executor.execute(script, work_dir)

        # 4. Commit and Push
        if vcs_handler.has_changes():
            commit_id = commit_info.get('id', 'unknown')
            modified_files = ', '.join(commit_info.get('modified', []))
            commit_message = f"CIツールによる自動生成コミット ({commit_id})\n\n変更トリガー: {modified_files}"
            
            logger.info(f"[{job_name}] 変更が検出されました。{target_branch} へプッシュします...")
            vcs_handler.commit_and_push(commit_message, target_branch)
            logger.info(f"[{job_name}] プッシュ成功。")
        else:
            logger.info(f"[{job_name}] 変更は検出されませんでした。")
        
        # 5. Cleanup Workspace
        workspace_manager.cleanup_workspace(job_name)

    except Exception as e:
        logger.exception(f"[{job_name}] ジョブが失敗しました: {e}")
