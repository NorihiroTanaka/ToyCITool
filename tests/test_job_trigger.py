"""JobTriggerService のテスト。"""

from unittest.mock import MagicMock

import pytest

from src.core.job_trigger import JobTriggerService
from src.core.config import Settings, GitConfig, JobConfig, RepoCISettings, RepoJobConfig
from src.core.interfaces import WebhookProvider, IJobService, IJobMatcher
from src.core.repo_ci_config_loader import RepoCIConfigLoader


@pytest.fixture
def mock_provider():
    provider = MagicMock(spec=WebhookProvider)
    provider.get_provider_id.return_value = "github"
    provider.should_skip.return_value = False
    provider.extract_changed_files.return_value = {"src/main.py"}
    provider.get_payload_meta.return_value = {"id": "abc123", "modified": ["src/main.py"]}
    # リポジトリ設定は使わない（ローカルジョブのみテスト）
    provider.extract_repo_info.return_value = None
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
def mock_repo_config_loader():
    loader = MagicMock(spec=RepoCIConfigLoader)
    loader.load_from_repo.return_value = None
    return loader


@pytest.fixture
def trigger_service(mock_settings, mock_job_service, mock_job_matcher, mock_repo_config_loader):
    return JobTriggerService(
        settings=mock_settings,
        job_service=mock_job_service,
        job_matcher=mock_job_matcher,
        repo_config_loader=mock_repo_config_loader,
    )


class TestJobTriggerService:
    def test_should_skipがTrueの場合に空リストが返る(
        self, trigger_service, mock_provider, mock_job_service
    ):
        mock_provider.should_skip.return_value = True
        result = trigger_service.process_webhook_event(mock_provider, {})
        assert result == []
        mock_job_service.submit_job.assert_not_called()

    def test_変更ファイルが空の場合に空リストが返る(
        self, trigger_service, mock_provider, mock_job_service
    ):
        mock_provider.extract_changed_files.return_value = set()
        result = trigger_service.process_webhook_event(mock_provider, {})
        assert result == []
        mock_job_service.submit_job.assert_not_called()

    def test_ジョブが1つマッチした場合にそのジョブ名が返る(
        self, trigger_service, mock_provider, mock_job_service
    ):
        result = trigger_service.process_webhook_event(mock_provider, {})
        assert result == ["test_job"]
        mock_job_service.submit_job.assert_called_once()

    def test_マッチしないジョブがスキップされる(
        self, trigger_service, mock_provider, mock_job_service, mock_job_matcher
    ):
        mock_job_matcher.match.return_value = False
        result = trigger_service.process_webhook_event(mock_provider, {})
        assert result == []
        mock_job_service.submit_job.assert_not_called()

    def test_submit_jobが正しい引数で呼ばれる(
        self, trigger_service, mock_provider, mock_job_service
    ):
        trigger_service.process_webhook_event(mock_provider, {})
        mock_job_service.submit_job.assert_called_once()
        call_args = mock_job_service.submit_job.call_args
        # 第1引数: job_dict (辞書)
        job_dict = call_args[0][0]
        assert job_dict["name"] == "test_job"
        # 第2引数: payload_meta
        payload_meta = call_args[0][1]
        assert payload_meta["id"] == "abc123"


class TestJobTriggerServiceRepoCIConfig:
    """リポジトリ内 .toyci.yaml を使ったジョブトリガーのテスト。"""

    @pytest.fixture
    def repo_info(self):
        return {"repo_url": "https://github.com/example/repo.git", "branch": "main"}

    @pytest.fixture
    def repo_ci_settings(self):
        return RepoCISettings(
            jobs=[
                RepoJobConfig(
                    name="repo_job",
                    script="pytest",
                    watch_files=["src/*.py"],
                )
            ]
        )

    @pytest.fixture
    def provider_with_repo(self, mock_provider, repo_info):
        mock_provider.extract_repo_info.return_value = repo_info
        return mock_provider

    def test_リポジトリCI設定のジョブがトリガーされる(
        self,
        mock_settings,
        mock_job_service,
        mock_job_matcher,
        provider_with_repo,
        repo_ci_settings,
    ):
        loader = MagicMock(spec=RepoCIConfigLoader)
        loader.load_from_repo.return_value = repo_ci_settings

        service = JobTriggerService(
            settings=mock_settings,
            job_service=mock_job_service,
            job_matcher=mock_job_matcher,
            repo_config_loader=loader,
        )
        result = service.process_webhook_event(provider_with_repo, {})

        assert "repo_job" in result
        # ローカルジョブ + リポジトリジョブの両方が呼ばれる
        assert mock_job_service.submit_job.call_count == 2

    def test_リポジトリCIジョブにrepo_urlとtarget_branchが補完される(
        self,
        mock_settings,
        mock_job_service,
        mock_job_matcher,
        provider_with_repo,
        repo_ci_settings,
        repo_info,
    ):
        loader = MagicMock(spec=RepoCIConfigLoader)
        loader.load_from_repo.return_value = repo_ci_settings

        service = JobTriggerService(
            settings=mock_settings,
            job_service=mock_job_service,
            job_matcher=mock_job_matcher,
            repo_config_loader=loader,
        )
        service.process_webhook_event(provider_with_repo, {})

        # 2回目の呼び出しがリポジトリジョブ
        repo_job_call = mock_job_service.submit_job.call_args_list[1]
        job_dict = repo_job_call[0][0]
        assert job_dict["repo_url"] == repo_info["repo_url"]
        assert job_dict["target_branch"] == repo_info["branch"]

    def test_リポジトリCI設定がない場合はローカルジョブのみ実行される(
        self,
        mock_settings,
        mock_job_service,
        mock_job_matcher,
        provider_with_repo,
    ):
        loader = MagicMock(spec=RepoCIConfigLoader)
        loader.load_from_repo.return_value = None

        service = JobTriggerService(
            settings=mock_settings,
            job_service=mock_job_service,
            job_matcher=mock_job_matcher,
            repo_config_loader=loader,
        )
        result = service.process_webhook_event(provider_with_repo, {})

        assert result == ["test_job"]
        assert mock_job_service.submit_job.call_count == 1

    def test_マッチしないリポジトリCIジョブはスキップされる(
        self,
        mock_settings,
        mock_job_service,
        provider_with_repo,
        repo_ci_settings,
    ):
        matcher = MagicMock(spec=IJobMatcher)
        # ローカルはマッチ、リポジトリジョブはマッチしない
        matcher.match.side_effect = [True, False]

        loader = MagicMock(spec=RepoCIConfigLoader)
        loader.load_from_repo.return_value = repo_ci_settings

        service = JobTriggerService(
            settings=mock_settings,
            job_service=mock_job_service,
            job_matcher=matcher,
            repo_config_loader=loader,
        )
        result = service.process_webhook_event(provider_with_repo, {})

        assert result == ["test_job"]
        assert mock_job_service.submit_job.call_count == 1
