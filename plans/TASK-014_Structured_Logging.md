# TASK-014: 構造化ログ（JSON形式）対応

## 1. タスク概要
ログ出力をJSON形式（構造化ログ）に対応させ、ログ収集ツール（Fluentd、Loki等）での解析・検索を容易にする。

## 2. 現状の課題
*   **現状:** Python標準の `logging` モジュールでテキスト形式のログを出力している。
*   **問題点:** テキストログはgrepベースの検索しかできず、複数フィールド（ジョブ名×ステータスなど）での絞り込みが困難。ログ量が増えるとテキストベースの解析が非現実的になる。

## 3. 仕様・要件

### コアコンセプトへの適合
*   **Docker非依存:** `python-json-logger` パッケージの追加のみ（軽量）。
*   **容易な設定:** `logging.yaml` に `format: json` を1行追加するだけで切り替え。デフォルトは従来のテキスト形式を維持。

### 実装内容
*   **対象ファイル:**
    *   `src/core/logging_config.py`: JSONフォーマッターの追加。
    *   `logging.yaml`: JSON出力設定の追記。

### ログ出力例
```json
{
  "timestamp": "2026-04-08T10:00:00.123Z",
  "level": "INFO",
  "logger": "src.core.job_service",
  "message": "ジョブ実行完了",
  "job_name": "Example",
  "job_id": "uuid-here",
  "status": "success",
  "duration_seconds": 45.2,
  "branch": "main",
  "commit": "abc1234"
}
```

### 期待される挙動
1.  `logging.yaml` の設定によりテキスト形式とJSON形式を切り替え可能。
2.  JSON形式の場合、ジョブ関連のコンテキスト情報（ジョブ名、ID、ブランチ等）を構造化フィールドとして付加する。
3.  コンソール出力はテキスト形式、ファイル出力はJSON形式といった混在構成も可能。
4.  既存のログ出力コードの変更は最小限に抑える（`logging.LoggerAdapter` や `extra` パラメータを活用）。

## 4. 優先度
**Low**
（ログ量が増えてきた段階、または外部ログ基盤と連携する段階で実装）
