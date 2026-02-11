import fnmatch
import logging
from typing import Dict, List, Any, Callable
from fastapi import BackgroundTasks

from .webhook_handler import WebhookProvider

logger = logging.getLogger(__name__)

class JobTriggerService:
    def __init__(self, config_loader: Callable[[], Dict[str, Any]], job_runner: Callable):
        """
        Args:
            config_loader: 設定ファイルを読み込む関数
            job_runner: ジョブを実行する関数 (run_job)
        """
        self.config_loader = config_loader
        self.job_runner = job_runner

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

        # 2. 設定をロード
        try:
            config = self.config_loader()
        except Exception as e:
            logger.error(f"設定の読み込みに失敗しました: {e}")
            return []
        
        # 3. ジョブを走査し、実行すべきものを特定
        triggered_jobs = []
        jobs = config.get("jobs", [])
        
        for job in jobs:
            watch_patterns = job.get("watch_files", [])
            job_name = job.get("name", "unknown")
            
            if self._should_run_job(changed_files, watch_patterns):
                logger.info(f"変更によりジョブ '{job_name}' がトリガーされました。")
                
                # 4. バックグラウンドタスクに追加
                try:
                    payload_meta = provider.get_payload_meta(payload)
                    background_tasks.add_task(self.job_runner, job, payload_meta)
                    triggered_jobs.append(job_name)
                except Exception as e:
                    logger.error(f"ジョブ '{job_name}' のトリガーに失敗しました: {e}")
            else:
                logger.debug(f"ジョブ '{job_name}' はスキップされました (一致するファイルなし)。")
                
        return triggered_jobs

    def _should_run_job(self, changed_files: set, watch_patterns: List[str]) -> bool:
        """変更ファイルが監視パターンにマッチするか判定する"""
        if not watch_patterns:
            return False

        for file in changed_files:
            for pattern in watch_patterns:
                if fnmatch.fnmatch(file, pattern):
                    return True
        return False
