from abc import ABC, abstractmethod
from typing import Dict, Any, List, Set, Optional

class IJobExecutor(ABC):
    @abstractmethod
    def execute(self, script: str, cwd: str) -> None:
        pass

class IVcsHandler(ABC):
    @abstractmethod
    def prepare_repository(self, url: str, branch: str, access_token: Optional[str] = None) -> None:
        pass
    
    @abstractmethod
    def has_changes(self) -> bool:
        pass

    @abstractmethod
    def commit_and_push(self, message: str, branch: str) -> None:
        pass

    @abstractmethod
    def repo_close(self) -> None:
        pass

class IJobService(ABC):
    @abstractmethod
    def run_job(self, job_config: Dict[str, Any], commit_info: Dict[str, Any]) -> None:
        pass

class IJobMatcher(ABC):
    @abstractmethod
    def match(self, job_config: Dict[str, Any], changed_files: Set[str]) -> bool:
        pass

class WebhookProvider(ABC):
    @abstractmethod
    def get_provider_id(self) -> str:
        """プロバイダー識別子を取得する"""
        pass

    @abstractmethod
    def should_skip(self, payload: Dict[str, Any]) -> bool:
        """このペイロードに基づいて処理をスキップすべきか判定する"""
        pass

    @abstractmethod
    def can_handle(self, headers: Dict[str, str]) -> bool:
        """このプロバイダーがリクエストを処理できるか判定する"""
        pass

    @abstractmethod
    def extract_changed_files(self, payload: Dict[str, Any]) -> Set[str]:
        """ペイロードから変更されたファイルのリストを抽出する"""
        pass
    
    @abstractmethod
    def get_payload_meta(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """ジョブ実行に必要なメタデータを抽出する"""
        pass
