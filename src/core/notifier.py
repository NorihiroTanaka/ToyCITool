"""通知機能モジュール。

ジョブの成功・失敗イベントを外部サービス（Discord等）に通知する。
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from urllib import request, error
import json

logger = logging.getLogger(__name__)


class NotificationEvent:
    """通知イベントのデータクラス。"""

    def __init__(
        self,
        job_name: str,
        success: bool,
        branch: str,
        commit_hash: str,
        commit_message: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        self.job_name = job_name
        self.success = success
        self.branch = branch
        self.commit_hash = commit_hash
        self.commit_message = commit_message
        self.error_message = error_message


class Notifier(ABC):
    """通知の基底クラス。"""

    @abstractmethod
    def notify(self, event: NotificationEvent) -> None:
        """通知を送信する。"""

    def _should_notify(self, event: NotificationEvent, on_success: bool, on_failure: bool) -> bool:
        if event.success:
            return on_success
        return on_failure


class DiscordNotifier(Notifier):
    """Discord Webhookへの通知実装。"""

    def __init__(
        self,
        webhook_url: str,
        on_success: bool = True,
        on_failure: bool = True,
    ) -> None:
        self._webhook_url = webhook_url
        self._on_success = on_success
        self._on_failure = on_failure

    def notify(self, event: NotificationEvent) -> None:
        if not self._should_notify(event, self._on_success, self._on_failure):
            return

        payload = self._build_payload(event)
        self._post(payload)

    def _build_payload(self, event: NotificationEvent) -> Dict[str, Any]:
        status_emoji = "✅" if event.success else "❌"
        status_label = "Success" if event.success else "Failure"
        color = 0x2ECC71 if event.success else 0xE74C3C  # green / red

        short_hash = event.commit_hash[:8] if event.commit_hash else "unknown"
        description_lines = [
            f"**Branch:** `{event.branch}`",
            f"**Commit:** `{short_hash}`",
        ]
        if event.commit_message:
            description_lines.append(f"**Message:** {event.commit_message}")
        if not event.success and event.error_message:
            description_lines.append(f"**Error:** {event.error_message}")

        embed = {
            "title": f"{status_emoji} [{event.job_name}] {status_label}",
            "description": "\n".join(description_lines),
            "color": color,
        }
        return {"embeds": [embed]}

    def _post(self, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            self._webhook_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=10) as resp:
                logger.debug(f"Discord通知を送信しました。 (status={resp.status})")
        except error.URLError as e:
            logger.warning(f"Discord通知の送信に失敗しました: {e}")
        except Exception as e:
            logger.warning(f"Discord通知で予期しないエラーが発生しました: {e}")


class CompositeNotifier(Notifier):
    """複数の通知先にまとめて送信するコンポジットクラス。"""

    def __init__(self, notifiers: List[Notifier]) -> None:
        self._notifiers = notifiers

    def notify(self, event: NotificationEvent) -> None:
        for notifier in self._notifiers:
            try:
                notifier.notify(event)
            except Exception as e:
                logger.warning(f"通知処理でエラーが発生しました: {e}")


class NullNotifier(Notifier):
    """通知設定がない場合の何もしないノットファイア。"""

    def notify(self, event: NotificationEvent) -> None:
        pass


def build_notifier(notifications_config: Optional[Dict[str, Any]]) -> Notifier:
    """設定から適切なNotifierを構築して返す。

    設定が空/未設定の場合は NullNotifier を返す（エラーにならない）。
    """
    if not notifications_config:
        return NullNotifier()

    notifiers: List[Notifier] = []

    discord_cfg = notifications_config.get("discord")
    if discord_cfg and isinstance(discord_cfg, dict):
        webhook_url = discord_cfg.get("webhook_url", "")
        if webhook_url:
            notifiers.append(
                DiscordNotifier(
                    webhook_url=webhook_url,
                    on_success=bool(discord_cfg.get("on_success", True)),
                    on_failure=bool(discord_cfg.get("on_failure", True)),
                )
            )
        else:
            logger.debug("Discord通知: webhook_urlが未設定のためスキップします。")

    if not notifiers:
        return NullNotifier()

    return CompositeNotifier(notifiers) if len(notifiers) > 1 else notifiers[0]
