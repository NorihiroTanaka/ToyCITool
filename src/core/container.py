from typing import Optional
import logging
from .config import Settings
from .job_service import JobService
from .job_trigger import JobTriggerService
from .job_matcher import JobMatcher
from .webhook_factory import WebhookProviderFactory
from .interfaces import IJobService

logger = logging.getLogger(__name__)

class Container:
    _instance: Optional["Container"] = None

    def __init__(self):
        self._settings: Optional[Settings] = None
        self._job_service: Optional[IJobService] = None
        self._job_trigger_service: Optional[JobTriggerService] = None

    @classmethod
    def get_instance(cls) -> "Container":
        if cls._instance is None:
            cls._instance = Container()
        return cls._instance

    @property
    def settings(self) -> Settings:
        if self._settings is None:
            self._settings = Settings.load()
            # ここでロギングの再設定などを行うことも可能
            # from .logging_config import setup_logging_from_settings
            # setup_logging_from_settings(self._settings)
        return self._settings

    @property
    def job_service(self) -> IJobService:
        if self._job_service is None:
            self._job_service = JobService(self.settings)
        return self._job_service

    @property
    def job_trigger_service(self) -> JobTriggerService:
        if self._job_trigger_service is None:
            self._job_trigger_service = JobTriggerService(
                settings=self.settings,
                job_service=self.job_service,
                job_matcher=JobMatcher()
            )
        return self._job_trigger_service
    
    # WebhookProviderFactoryはクラスメソッドを使用しているため、ここでインスタンス化する必要はないかもしれないが、
    # 将来的にはここを通すように統一しても良い。今回は静的メソッドとして利用する。

def get_container() -> Container:
    return Container.get_instance()
