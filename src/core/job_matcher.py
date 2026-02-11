import fnmatch
from typing import Set, Dict, Any, List
import logging

logger = logging.getLogger(__name__)

from .interfaces import IJobMatcher

class JobMatcher(IJobMatcher):
    """ジョブの実行条件を判定するクラス"""

    def match(self, job_config: Dict[str, Any], changed_files: Set[str]) -> bool:
        """
        ジョブ設定と変更ファイルリストに基づき、ジョブを実行すべきか判定する。
        
        Args:
            job_config: ジョブの設定辞書
            changed_files: 変更されたファイルのセット

        Returns:
            実行すべきであれば True
        """
        watch_patterns = job_config.get("watch_files", [])
        return self.match_files(watch_patterns, changed_files)

    def match_files(self, patterns: List[str], files: Set[str]) -> bool:
        """
        ファイルリストがパターンにマッチするか判定する。

        Args:
            patterns: 監視対象のファイルパターンリスト (glob形式)
            files: 変更されたファイルのセット
        
        Returns:
            一つでもマッチすれば True
        """
        if not patterns:
            return False

        for file in files:
            for pattern in patterns:
                if fnmatch.fnmatch(file, pattern):
                    return True
        return False
