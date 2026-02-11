import logging
from abc import ABC, abstractmethod
from typing import Set, Dict, Any, Optional, List

logger = logging.getLogger(__name__)

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

class GitHubProvider(WebhookProvider):
    def get_provider_id(self) -> str:
        return "github"

    def should_skip(self, payload: Dict[str, Any]) -> bool:
        message = payload.get("head_commit", {}).get("message", "").lower()
        return "ci skip" in message or "[ci skip]" in message

    def can_handle(self, headers: Dict[str, str]) -> bool:
        # FastAPI の headers は case-insensitive だが、念のため小文字でチェック
        # headers オブジェクト自体は Headers クラスで key 検索は case-insensitive
        # ここでは dict に変換されたものを想定するか、Headers オブジェクトの振る舞いに依存するか
        # 汎用性を高めるため、キーを小文字に変換してチェックする
        headers_lower = {k.lower(): v for k, v in headers.items()}
        return "x-github-event" in headers_lower

    def extract_changed_files(self, payload: Dict[str, Any]) -> Set[str]:
        changed_files = set()
        commits = payload.get("commits", [])
        if not commits:
            return changed_files
            
        for commit in commits:
            changed_files.update(commit.get("added", []))
            changed_files.update(commit.get("modified", []))
            changed_files.update(commit.get("removed", []))
        return changed_files

    def get_payload_meta(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        GitHub ペイロードからメタデータを抽出する
        現在は最新のコミット情報を返す（既存ロジック互換）
        """
        commits = payload.get("commits", [])
        return commits[-1] if commits else {}

class WebhookProviderFactory:
    _providers: List[WebhookProvider] = [
        GitHubProvider(),
    ]

    @classmethod
    def get_provider(cls, headers: Dict[str, str]) -> WebhookProvider:
        """
        リクエストヘッダーに基づいて適切なプロバイダーを返す。
        マッチしない場合はデフォルト（GitHub）を返す。
        """
        for provider in cls._providers:
            if provider.can_handle(headers):
                return provider
        
        # フォールバック: GitHub
        logger.info("ヘッダーに一致するプロバイダーが見つかりませんでした。GitHubProvider にフォールバックします。")
        return cls._providers[0]
