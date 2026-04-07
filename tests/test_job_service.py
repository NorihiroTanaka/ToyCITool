import pytest
from contextlib import contextmanager
from unittest.mock import MagicMock, patch
from src.core.job_service import JobService
from src.core.vcs_handler import GitHandler
from src.core.job_executor import ShellJobExecutor
from src.core.workspace_manager import WorkspaceManager
from src.core.config import Settings, GitConfig
from src.core.exceptions import JobValidationError


@pytest.fixture
def mock_settings():
    settings = Settings(
        git=GitConfig(access_token="test_token", repo_url="https://github.com/example/default.git")
    )
    return settings


@pytest.fixture
def mock_workspace_manager():
    wm = MagicMock(spec=WorkspaceManager)
    wm.prepare_workspace.return_value = "/tmp/test_workspace"
    # workspace_lock はコンテキストマネージャとして動作するよう設定
    @contextmanager
    def _noop_lock(job_name):
        yield
    wm.workspace_lock.side_effect = _noop_lock
    return wm


@pytest.fixture
def mock_vcs_handler():
    handler = MagicMock(spec=GitHandler)
    handler.has_changes.return_value = False
    handler.__enter__ = MagicMock(return_value=handler)
    handler.__exit__ = MagicMock(return_value=False)
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
    mock_workspace_manager.workspace_lock.assert_called_once_with("test_job")
    mock_workspace_manager.prepare_workspace.assert_called_once_with("test_job")
    mock_vcs_handler_cls.assert_called_once_with("/tmp/test_workspace")
    mock_vcs_handler.prepare_repository.assert_called_once()
    mock_job_executor.execute.assert_called_once()
    call_kwargs = mock_job_executor.execute.call_args
    assert call_kwargs[0][0] == "echo 'hello'"
    assert call_kwargs[0][1] == "/tmp/test_workspace"
    assert call_kwargs[1]["job_name"] == "test_job"
    env = call_kwargs[1]["env"]
    assert "CI_JOB_ID" in env
    assert env["CI_COMMIT_HASH"] == "123"
    assert env["CI_BRANCH"] == "main"
    assert env["CI_REPO_URL"] == "https://github.com/example/repo.git"
    assert env["CI_WORKSPACE"] == "/tmp/test_workspace"
    mock_workspace_manager.cleanup_workspace.assert_called_once_with("test_job")

    service.shutdown()


def test_job_service_run_job_with_changes(mock_settings, mock_workspace_manager, mock_vcs_handler_cls, mock_job_executor_cls, mock_vcs_handler):
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

    mock_vcs_handler.commit_and_push.assert_called_once()
    args, _ = mock_vcs_handler.commit_and_push.call_args
    assert "abc" in args[0]
    assert "develop" == args[1]

    service.shutdown()


def test_job_service_user_env_merged_with_ci_env(mock_settings, mock_workspace_manager, mock_vcs_handler_cls, mock_job_executor_cls, mock_vcs_handler, mock_job_executor):
    """ユーザー定義の環境変数がCI変数とマージされること"""
    service = JobService(
        settings=mock_settings,
        workspace_manager=mock_workspace_manager,
        vcs_handler_cls=mock_vcs_handler_cls,
        job_executor_cls=mock_job_executor_cls
    )

    job_info = {
        "name": "env_test_job",
        "repo_url": "https://github.com/example/repo.git",
        "target_branch": "develop",
        "script": "echo 'test'",
        "env": {"MY_VAR": "my_value", "BUILD_TYPE": "release"},
    }
    commit_info = {"id": "def456", "modified": ["file.py"]}

    service.run_job(job_info, commit_info)

    call_kwargs = mock_job_executor.execute.call_args
    env = call_kwargs[1]["env"]
    assert env["MY_VAR"] == "my_value"
    assert env["BUILD_TYPE"] == "release"
    assert env["CI_COMMIT_HASH"] == "def456"
    assert env["CI_BRANCH"] == "develop"

    service.shutdown()


def test_job_service_ci_env_overrides_user_env(mock_settings, mock_workspace_manager, mock_vcs_handler_cls, mock_job_executor_cls, mock_vcs_handler, mock_job_executor):
    """CI変数がユーザー定義の同名変数を上書きすること"""
    service = JobService(
        settings=mock_settings,
        workspace_manager=mock_workspace_manager,
        vcs_handler_cls=mock_vcs_handler_cls,
        job_executor_cls=mock_job_executor_cls
    )

    job_info = {
        "name": "override_test",
        "repo_url": "https://github.com/example/repo.git",
        "target_branch": "main",
        "script": "echo 'test'",
        "env": {"CI_BRANCH": "user_branch"},
    }
    commit_info = {"id": "abc123", "modified": []}

    service.run_job(job_info, commit_info)

    call_kwargs = mock_job_executor.execute.call_args
    env = call_kwargs[1]["env"]
    assert env["CI_BRANCH"] == "main"

    service.shutdown()


def test_job_service_passes_job_timeout_to_executor(mock_settings, mock_workspace_manager, mock_vcs_handler_cls, mock_job_executor_cls, mock_vcs_handler, mock_job_executor):
    """ジョブ固有のtimeoutがexecutorに渡されること"""
    service = JobService(
        settings=mock_settings,
        workspace_manager=mock_workspace_manager,
        vcs_handler_cls=mock_vcs_handler_cls,
        job_executor_cls=mock_job_executor_cls
    )

    job_info = {
        "name": "timeout_test",
        "repo_url": "https://github.com/example/repo.git",
        "target_branch": "main",
        "script": "echo 'hello'",
        "timeout": 600,
    }
    commit_info = {"id": "123", "modified": []}

    service.run_job(job_info, commit_info)

    call_kwargs = mock_job_executor.execute.call_args
    assert call_kwargs[1]["timeout_seconds"] == 600

    service.shutdown()


def test_job_service_uses_default_timeout_when_job_has_no_timeout(mock_settings, mock_workspace_manager, mock_vcs_handler_cls, mock_job_executor_cls, mock_vcs_handler, mock_job_executor):
    """ジョブにtimeoutが未設定の場合、default_timeoutが使われること"""
    service = JobService(
        settings=mock_settings,
        workspace_manager=mock_workspace_manager,
        vcs_handler_cls=mock_vcs_handler_cls,
        job_executor_cls=mock_job_executor_cls
    )

    job_info = {
        "name": "no_timeout_test",
        "repo_url": "https://github.com/example/repo.git",
        "target_branch": "main",
        "script": "echo 'hello'",
    }
    commit_info = {"id": "123", "modified": []}

    service.run_job(job_info, commit_info)

    call_kwargs = mock_job_executor.execute.call_args
    assert call_kwargs[1]["timeout_seconds"] == mock_settings.default_timeout

    service.shutdown()


def test_job_service_validation_error(mock_settings):
    service = JobService(settings=mock_settings)

    job_info = {
        "name": "invalid_job",
        "repo_url": "http://example.com",
        "target_branch": "main",
        # "script" is missing
    }
    commit_info = {}

    with pytest.raises(JobValidationError):
        service.run_job(job_info, commit_info)

    service.shutdown()


def test_job_service_submit_job_queues_and_executes(mock_settings, mock_workspace_manager, mock_vcs_handler_cls, mock_job_executor_cls, mock_vcs_handler, mock_job_executor):
    """submit_job がキューを通じてジョブを実行すること"""
    service = JobService(
        settings=mock_settings,
        workspace_manager=mock_workspace_manager,
        vcs_handler_cls=mock_vcs_handler_cls,
        job_executor_cls=mock_job_executor_cls
    )

    job_info = {
        "name": "queued_job",
        "repo_url": "https://github.com/example/repo.git",
        "target_branch": "main",
        "script": "echo 'queued'",
    }
    commit_info = {"id": "999", "modified": []}

    service.submit_job(job_info, commit_info)
    service._job_queue.join()  # キューが空になるまで待機

    mock_job_executor.execute.assert_called_once()

    service.shutdown()
