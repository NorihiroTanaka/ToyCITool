# TASK-011: Slack通知チャネル対応

## 1. タスク概要
TASK-005で実装した通知機能の拡張として、Slack Incoming Webhookによる通知チャネルを追加する。

## 2. 現状の課題
*   **現状:** 通知はDiscord Webhookのみ対応。`Notifier` 基底クラスによる拡張設計は整っている。
*   **問題点:** 業務環境ではSlackが主要なコミュニケーションツールであることが多く、Discord対応だけでは利用シーンが限られる。

## 3. 仕様・要件

### コアコンセプトへの適合
*   **Docker非依存:** HTTPリクエスト送信のみ。
*   **容易な設定:** `config.yaml` に `webhook_url` を1行追加するだけ。

### 実装内容
*   **対象ファイル:**
    *   `src/core/notifier.py`: `SlackNotifier` クラスの追加。
    *   `src/core/config.py`: Slack通知設定の追加。
    *   `src/core/container.py`: DI登録の拡張。

### 設定ファイル
```yaml
notifications:
  slack:
    webhook_url: ${SLACK_WEBHOOK_URL}
    on_success: true
    on_failure: true
    channel: "#ci-notifications"  # オプション
```

### 通知フォーマット
*   Slack Block Kit形式でリッチなメッセージを送信する。
*   成功時は緑、失敗時は赤のサイドバー（attachment color）。
*   含める情報: ジョブ名、ステータス、ブランチ、コミットハッシュ、エラーメッセージ（失敗時）。

## 4. 優先度
**Low**
（Discord通知と同じパターンで実装可能。必要に応じて追加する）
