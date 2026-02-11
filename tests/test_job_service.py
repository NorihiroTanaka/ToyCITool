import os
import shutil
import tempfile
import pytest
from unittest.mock import MagicMock, patch
from src.core.job_service import JobService
from src.core.vcs_handler import GitHandler
from src.core.job_executor import ShellJobExecutor
from src.core.workspace_manager import WorkspaceManager
from src.core.config import Settings, GitConfig

@pytest.fixture
def mock_settings():
    settings = Settings(
        git=GitConfig(accessToken="test_token", repo_url="https://github.com/example/default.git")
    )
    return settings

@pytest.fixture
def mock_workspace_manager():
    wm = MagicMock(spec=WorkspaceManager)
    wm.prepare_workspace.return_value = "/tmp/test_workspace"
    return wm

@pytest.fixture
def mock_vcs_handler():
    handler = MagicMock(spec=GitHandler)
    handler.has_changes.return_value = False
    return handler

@pytest.fixture
def mock_vcs_handler_cls(mock_vcs_handler):
    cls = MagicMock()
    cls.return_value = mock_vcs_handler
    return cls

@pytest.fixture
def mock_job_executor():
    executor = MagicMock(spec=ShellJobExecutor)
    return executor

@pytest.fixture
def mock_job_executor_cls(mock_job_executor):
    cls = MagicMock()
    cls.return_value = mock_job_executor
    return cls

def test_job_service_run_job_success(mock_settings, mock_workspace_manager, mock_vcs_handler_cls, mock_job_executor_cls, mock_vcs_handler, mock_job_executor):
    service = JobService(
        settings=mock_settings,
        workspace_manager=mock_workspace_manager,
        vcs_handler_cls=mock_vcs_handler_cls,
        job_executor_cls=mock_job_executor_cls
    )

    job_info = {
        "name": "test_job",
        "repo_url": "https://github.com/example/repo.git",
        "target_branch": "main",
        "script": "echo 'hello'"
    }
    commit_info = {"id": "123", "modified": []}

    service.run_job(job_info, commit_info)

    # 検証
    mock_workspace_manager.prepare_workspace.assert_called_once_with("test_job")
    mock_vcs_handler_cls.assert_called_once_with("/tmp/test_workspace")
    mock_vcs_handler.prepare_repository.assert_called_once()
    mock_job_executor.execute.assert_called_once_with("echo 'hello'", "/tmp/test_workspace")
    mock_workspace_manager.cleanup_workspace.assert_called_once_with("test_job")

def test_job_service_run_job_with_changes(mock_settings, mock_workspace_manager, mock_vcs_handler_cls, mock_job_executor_cls, mock_vcs_handler):
    # 変更がある場合のモック設定
    mock_vcs_handler.has_changes.return_value = True
    
    service = JobService(
        settings=mock_settings,
        workspace_manager=mock_workspace_manager,
        vcs_handler_cls=mock_vcs_handler_cls,
        job_executor_cls=mock_job_executor_cls
    )

    job_info = {
        "name": "test_job_changes",
        "repo_url": "https://github.com/example/repo.git",
        "target_branch": "develop",
        "script": "echo 'build'"
    }
    commit_info = {"id": "abc", "modified": ["file1.txt"]}

    service.run_job(job_info, commit_info)

    # 検証: コミットとプッシュが呼ばれたか
    mock_vcs_handler.commit_and_push.assert_called_once()
    args, _ = mock_vcs_handler.commit_and_push.call_args
    assert "abc" in args[0]  # メッセージにコミットIDが含まれているか
    assert "develop" == args[1] # ブランチ名が正しいか

def test_job_service_validation_error(mock_settings):
    service = JobService(settings=mock_settings)
    
    # 必須パラメータ欠損 (scriptがない)
    job_info = {
        "name": "invalid_job",
        "repo_url": "http://example.com",
        "target_branch": "main",
        # "script" is missing
    }
    commit_info = {}

    # エラーにならずにreturnされることを確認（ログ出力のみ）
    service.run_job(job_info, commit_info)
    # ここではログの検証は省略するが、例外が飛ばないことを確認
