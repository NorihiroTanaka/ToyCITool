import logging
from typing import Set, Dict, Any

from .interfaces import WebhookProvider

logger = logging.getLogger(__name__)

class GitHubProvider(WebhookProvider):
    def get_provider_id(self) -> str:
        return "github"

    def should_skip(self, payload: Dict[str, Any]) -> bool:
        message = payload.get("head_commit", {}).get("message", "").lower()
        return "skip ci" in message or "[skip ci]" in message

    def can_handle(self, headers: Dict[str, str]) -> bool:
        # ヘッダーキーの大文字小文字を無視してチェック
        return any(k.lower() == "x-github-event" for k in headers.keys())

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
