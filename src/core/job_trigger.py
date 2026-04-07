import logging
from typing import Dict, List, Any, Optional

from .interfaces import WebhookProvider, IJobMatcher, IJobService
from .job_matcher import JobMatcher
from .config import Settings
from .repo_ci_config_loader import RepoCIConfigLoader

logger = logging.getLogger(__name__)

class JobTriggerService:
    def __init__(
        self,
        settings: Settings,
        job_service: IJobService,
        job_matcher: Optional[IJobMatcher] = None,
        repo_config_loader: Optional[RepoCIConfigLoader] = None,
    ):
        """
        Args:
            settings: 設定オブジェクト
            job_service: ジョブサービス
            job_matcher: ジョブ実行条件を判定するマッチャー (省略時はデフォルトを使用)
            repo_config_loader: リポジトリ内 CI 設定ローダー (省略時はデフォルトを使用)
        """
        self.settings = settings
        self.job_service = job_service
        self.job_matcher = job_matcher or JobMatcher()
        self._repo_config_loader = repo_config_loader or RepoCIConfigLoader(
            access_token=settings.git.access_token
        )

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
        payload_meta = provider.get_payload_meta(payload)

        # ローカル config.yaml に定義されたジョブを処理
        for job_config in self.settings.jobs:
            job_dict = job_config.model_dump()
            job_name = job_config.name

            if self.job_matcher.match(job_dict, changed_files):
                logger.info(f"変更によりジョブ '{job_name}' がトリガーされました。")
                try:
                    self.job_service.submit_job(job_dict, payload_meta)
                    triggered_jobs.append(job_name)
                except Exception as e:
                    logger.error(f"ジョブ '{job_name}' のキュー追加に失敗しました: {e}")
            else:
                logger.debug(f"ジョブ '{job_name}' はスキップされました (一致するファイルなし)。")

        # トリガーリポジトリ内の .toyci.yaml に定義されたジョブを処理
        repo_info = provider.extract_repo_info(payload)
        if repo_info:
            self._process_repo_ci_jobs(repo_info, changed_files, payload_meta, triggered_jobs)

        return triggered_jobs

    def _process_repo_ci_jobs(
        self,
        repo_info: Dict[str, str],
        changed_files: set,
        payload_meta: Dict[str, Any],
        triggered_jobs: List[str],
    ) -> None:
        """リポジトリ内の .toyci.yaml からジョブを読み込み、マッチするものをキューに追加する。"""
        repo_url = repo_info["repo_url"]
        branch = repo_info["branch"]

        repo_settings = self._repo_config_loader.load_from_repo(repo_url, branch)
        if not repo_settings:
            return

        for repo_job in repo_settings.jobs:
            job_dict = repo_job.model_dump()
            # repo_url / target_branch を Webhook ペイロードの情報で補完
            job_dict["repo_url"] = repo_url
            job_dict["target_branch"] = branch

            job_name = repo_job.name
            if self.job_matcher.match(job_dict, changed_files):
                logger.info(
                    f"リポジトリ CI 設定によりジョブ '{job_name}' がトリガーされました。"
                )
                try:
                    self.job_service.submit_job(job_dict, payload_meta)
                    triggered_jobs.append(job_name)
                except Exception as e:
                    logger.error(
                        f"リポジトリ CI ジョブ '{job_name}' のキュー追加に失敗しました: {e}"
                    )
            else:
                logger.debug(
                    f"リポジトリ CI ジョブ '{job_name}' はスキップされました (一致するファイルなし)。"
                )
