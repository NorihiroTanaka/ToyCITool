import logging
from typing import Dict, List, Any, Callable, Optional
from fastapi import BackgroundTasks

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

    def process_webhook_event(self, provider: WebhookProvider, payload: Dict[str, Any], background_tasks: BackgroundTasks) -> List[str]:
        """
        Webhookイベントを処理し、条件に合致するジョブをトリガーする。

        Args:
            provider: Webhookプロバイダー
            payload: Webhookペイロード
            background_tasks: FastAPIのバックグラウンドタスク管理オブジェクト

        Returns:
            トリガーされたジョブ名のリスト
        """

        should_skip = provider.should_skip(payload)
        if should_skip:
            logger.info(f"ペイロードに基づいてプロバイダー {provider.get_provider_id()} の処理をスキップします。")
            return []

        # 1. プロバイダーを使って変更ファイルを抽出
        changed_files = provider.extract_changed_files(payload)
        logger.info(f"{provider.get_provider_id()} によって抽出された変更ファイル: {changed_files}")
        
        if not changed_files:
             # 変更ファイルがない場合は処理終了（pingイベントなど）
             return []

        # 2. 設定（Settings）は既にロードされている
        
        # 3. ジョブを走査し、実行すべきものを特定
        triggered_jobs = []
        jobs = self.settings.jobs
        
        for job_config in jobs:
            # Pydanticモデルから辞書へ変換、またはそのまま使う
            # IJobMatcher.match は Dictを受け取る想定だが、Pydanticモデルも属性アクセスできる。
            # 一旦 model_dump() して辞書として扱うのが安全かもしれないが、ここでは辞書として渡す
            job_dict = job_config.model_dump()
            job_name = job_config.name
            
            if self.job_matcher.match(job_dict, changed_files):
                logger.info(f"変更によりジョブ '{job_name}' がトリガーされました。")
                
                # 4. バックグラウンドタスクに追加
                try:
                    payload_meta = provider.get_payload_meta(payload)
                    background_tasks.add_task(self.job_service.run_job, job_dict, payload_meta)
                    triggered_jobs.append(job_name)
                except Exception as e:
                    logger.error(f"ジョブ '{job_name}' のトリガーに失敗しました: {e}")
            else:
                logger.debug(f"ジョブ '{job_name}' はスキップされました (一致するファイルなし)。")
                
        return triggered_jobs

