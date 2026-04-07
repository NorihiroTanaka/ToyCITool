"""リポジトリ内の CI 設定ファイル (.toyci.yaml) を読み込むローダー。"""

import logging
import os
import tempfile
from typing import Optional

import yaml

from .config import RepoCISettings
from .vcs_handler import GitHandler

logger = logging.getLogger(__name__)

REPO_CI_CONFIG_FILE = ".toyci.yaml"


class RepoCIConfigLoader:
    """リポジトリをシャロークローンして .toyci.yaml を読み込む。"""

    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token

    def load_from_repo(self, repo_url: str, branch: str) -> Optional[RepoCISettings]:
        """リポジトリをクローンし、CI 設定ファイルを読み込んで返す。

        クローンは一時ディレクトリに行い、読み込み後に自動削除される。
        設定ファイルが存在しない場合や読み込みに失敗した場合は None を返す。
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            handler = GitHandler(tmp_dir)
            try:
                handler.prepare_repository(repo_url, branch, self.access_token)
                return self.load_from_path(tmp_dir)
            except Exception as e:
                logger.warning(
                    f"リポジトリからの CI 設定読み込みに失敗しました"
                    f" ({repo_url}@{branch}): {e}"
                )
                return None
            finally:
                handler.close()

    def load_from_path(self, repo_path: str) -> Optional[RepoCISettings]:
        """クローン済みディレクトリから .toyci.yaml を読み込んで返す。"""
        config_path = os.path.join(repo_path, REPO_CI_CONFIG_FILE)
        if not os.path.exists(config_path):
            logger.debug(f"リポジトリに CI 設定ファイルがありません: {config_path}")
            return None

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            settings = RepoCISettings(**data)
            logger.info(
                f"リポジトリの CI 設定を読み込みました: {REPO_CI_CONFIG_FILE}"
                f" ({len(settings.jobs)} ジョブ)"
            )
            return settings
        except Exception as e:
            logger.warning(f"CI 設定ファイルの解析に失敗しました ({config_path}): {e}")
            return None
