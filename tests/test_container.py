"""Container のテスト。"""

from unittest.mock import patch

import pytest

from src.core.container import Container, get_container
from src.core.config import Settings
from src.core.interfaces import IJobService
from src.core.job_trigger import JobTriggerService


class TestContainer:
    def setup_method(self):
        """各テスト前にシングルトンをリセット。"""
        Container._instance = None

    def teardown_method(self):
        """各テスト後にシングルトンをリセット。"""
        Container._instance = None

    def test_get_instanceがシングルトンである(self):
        c1 = Container.get_instance()
        c2 = Container.get_instance()
        assert c1 is c2

    @patch.object(Settings, "load")
    def test_settingsプロパティがSettingsを返す(self, mock_load):
        mock_load.return_value = Settings()
        container = Container.get_instance()
        settings = container.settings
        assert isinstance(settings, Settings)
        mock_load.assert_called_once()

    @patch.object(Settings, "load")
    def test_settingsは一度だけロードされる(self, mock_load):
        mock_load.return_value = Settings()
        container = Container.get_instance()
        _ = container.settings
        _ = container.settings
        mock_load.assert_called_once()

    @patch.object(Settings, "load")
    def test_job_serviceプロパティがIJobService実装を返す(self, mock_load):
        mock_load.return_value = Settings()
        container = Container.get_instance()
        service = container.job_service
        assert isinstance(service, IJobService)

    @patch.object(Settings, "load")
    def test_job_trigger_serviceプロパティがJobTriggerServiceを返す(self, mock_load):
        mock_load.return_value = Settings()
        container = Container.get_instance()
        trigger = container.job_trigger_service
        assert isinstance(trigger, JobTriggerService)

    def test_get_container関数がContainerインスタンスを返す(self):
        with patch.object(Settings, "load", return_value=Settings()):
            container = get_container()
            assert isinstance(container, Container)
