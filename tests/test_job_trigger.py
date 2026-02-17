"""JobTriggerService のテスト。"""

from unittest.mock import MagicMock

import pytest

from src.core.job_trigger import JobTriggerService
from src.core.config import Settings, GitConfig, JobConfig
from src.core.interfaces import WebhookProvider, IJobService, IJobMatcher


@pytest.fixture
def mock_provider():
    provider = MagicMock(spec=WebhookProvider)
    provider.get_provider_id.return_value = "github"
    provider.should_skip.return_value = False
    provider.extract_changed_files.return_value = {"src/main.py"}
    provider.get_payload_meta.return_value = {"id": "abc123", "modified": ["src/main.py"]}
    return provider


@pytest.fixture
def mock_job_service():
    return MagicMock(spec=IJobService)


@pytest.fixture
def mock_job_matcher():
    matcher = MagicMock(spec=IJobMatcher)
    matcher.match.return_value = True
    return matcher


@pytest.fixture
def mock_background_tasks():
    return MagicMock()


@pytest.fixture
def trigger_service(mock_settings, mock_job_service, mock_job_matcher):
    return JobTriggerService(
        settings=mock_settings,
        job_service=mock_job_service,
        job_matcher=mock_job_matcher,
    )


class TestJobTriggerService:
    def test_should_skipがTrueの場合に空リストが返る(
        self, trigger_service, mock_provider, mock_background_tasks
    ):
        mock_provider.should_skip.return_value = True
        result = trigger_service.process_webhook_event(
            mock_provider, {}, mock_background_tasks
        )
        assert result == []
        mock_background_tasks.add_task.assert_not_called()

    def test_変更ファイルが空の場合に空リストが返る(
        self, trigger_service, mock_provider, mock_background_tasks
    ):
        mock_provider.extract_changed_files.return_value = set()
        result = trigger_service.process_webhook_event(
            mock_provider, {}, mock_background_tasks
        )
        assert result == []

    def test_ジョブが1つマッチした場合にそのジョブ名が返る(
        self, trigger_service, mock_provider, mock_background_tasks
    ):
        result = trigger_service.process_webhook_event(
            mock_provider, {}, mock_background_tasks
        )
        assert result == ["test_job"]
        mock_background_tasks.add_task.assert_called_once()

    def test_マッチしないジョブがスキップされる(
        self, trigger_service, mock_provider, mock_background_tasks, mock_job_matcher
    ):
        mock_job_matcher.match.return_value = False
        result = trigger_service.process_webhook_event(
            mock_provider, {}, mock_background_tasks
        )
        assert result == []
        mock_background_tasks.add_task.assert_not_called()

    def test_background_tasksにadd_taskが正しい引数で呼ばれる(
        self, trigger_service, mock_provider, mock_background_tasks, mock_job_service
    ):
        trigger_service.process_webhook_event(
            mock_provider, {}, mock_background_tasks
        )
        mock_background_tasks.add_task.assert_called_once()
        call_args = mock_background_tasks.add_task.call_args
        # 第1引数: job_service.run_job
        assert call_args[0][0] == mock_job_service.run_job
        # 第2引数: job_dict (辞書)
        job_dict = call_args[0][1]
        assert job_dict["name"] == "test_job"
        # 第3引数: payload_meta
        payload_meta = call_args[0][2]
        assert payload_meta["id"] == "abc123"
