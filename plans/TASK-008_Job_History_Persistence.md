# TASK-008: ジョブ履歴の永続化（SQLite）

## 1. タスク概要
ジョブの実行履歴（開始時刻、終了時刻、ステータス、トリガー情報など）をSQLiteデータベースに保存し、再起動後も参照可能にする。

## 2. 現状の課題
*   **現状:** ジョブの実行状態はインメモリで管理されており、プロセス再起動時に全履歴が失われる。
*   **問題点:** 過去のビルド結果を振り返れない。障害調査時に「いつ何が実行されたか」を追跡できない。統計的な分析（成功率、平均実行時間など）もできない。

## 3. 仕様・要件

### コアコンセプトへの適合
*   **Docker非依存:** SQLiteはPython標準ライブラリ `sqlite3` に含まれ、追加依存なし。
*   **容易な設定:** デフォルトでプロジェクトルートに `toyci.db` を作成。パスは `config.yaml` でオーバーライド可能。

### 実装内容
*   **対象ファイル:**
    *   `src/core/job_history.py` (新規作成): 履歴の永続化ロジック。
    *   `src/core/interfaces.py`: `IJobHistoryRepository` インターフェースの定義。
    *   `src/core/job_service.py`: ジョブ開始/終了時に履歴を記録する呼び出し追加。
    *   `src/core/container.py`: DI登録。

### データモデル
```sql
CREATE TABLE job_runs (
    id TEXT PRIMARY KEY,          -- UUID
    job_name TEXT NOT NULL,
    status TEXT NOT NULL,          -- 'running', 'success', 'failure', 'timeout'
    started_at TEXT NOT NULL,      -- ISO 8601
    finished_at TEXT,
    duration_seconds REAL,
    trigger_branch TEXT,
    trigger_commit TEXT,
    trigger_message TEXT,
    error_message TEXT,
    log_file_path TEXT
);
```

### 期待される挙動
1.  ジョブ開始時に `status=running` でレコードを挿入する。
2.  ジョブ完了時に `status`, `finished_at`, `duration_seconds`, `error_message` を更新する。
3.  履歴はAPIエンドポイント（`GET /api/jobs/history`）から取得可能にする。
4.  クエリパラメータでフィルタ可能（ジョブ名、ステータス、日付範囲）。

### 保持ポリシー
*   設定で `history_retention_days` を指定可能（デフォルト: 90日）。
*   起動時またはジョブ完了時に古いレコードを自動削除する。

## 4. 優先度
**Medium**
（TASK-006のWebダッシュボードの前提となる機能。単独でもAPI経由で価値を提供できる）
