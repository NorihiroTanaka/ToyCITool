import logging
from typing import Dict, List, Any, Optional

from .interfaces import WebhookProvider, IJobMatcher, IJobService
from .job_matcher import JobMatcher
from .config import Settings

logger = logging.getLogger(__name__)

class JobTriggerService:
    def __init__(self, settings: Settings, job_service: IJobService, job_matcher: Optional[IJobMatcher] = None):
        """
        Args:
            settings: 設定オブジェクト
            job_service: ジョブサービス
            job_matcher: ジョブ実行条件を判定するマッチャー (省略時はデフォルトを使用)
        """
        self.settings = settings
        self.job_service = job_service
        self.job_matcher = job_matcher or JobMatcher()

    def process_webhook_event(self, provider: WebhookProvider, payload: Dict[str, Any]) -> List[str]:
        """
        Webhookイベントを処理し、条件に合致するジョブをキューに追加する。

        Args:
            provider: Webhookプロバイダー
            payload: Webhookペイロード

        Returns:
            キューに追加されたジョブ名のリスト
        """

        should_skip = provider.should_skip(payload)
        if should_skip:
            logger.info(f"ペイロードに基づいてプロバイダー {provider.get_provider_id()} の処理をスキップします。")
            return []

        changed_files = provider.extract_changed_files(payload)
        logger.info(f"{provider.get_provider_id()} によって抽出された変更ファイル: {changed_files}")

        if not changed_files:
            return []

        triggered_jobs = []
        jobs = self.settings.jobs

        for job_config in jobs:
            job_dict = job_config.model_dump()
            job_name = job_config.name

            if self.job_matcher.match(job_dict, changed_files):
                logger.info(f"変更によりジョブ '{job_name}' がトリガーされました。")

                try:
                    payload_meta = provider.get_payload_meta(payload)
                    self.job_service.submit_job(job_dict, payload_meta)
                    triggered_jobs.append(job_name)
                except Exception as e:
                    logger.error(f"ジョブ '{job_name}' のキュー追加に失敗しました: {e}")
            else:
                logger.debug(f"ジョブ '{job_name}' はスキップされました (一致するファイルなし)。")

        return triggered_jobs
