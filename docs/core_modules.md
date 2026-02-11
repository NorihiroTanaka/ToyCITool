# コアモジュール詳細

`src/core/` ディレクトリに含まれる主要なモジュールの詳細説明です。

## 1. JobService (`src/core/job_service.py`)

CIジョブの実行ライフサイクルを管理するサービスクラスです。

### `JobService` クラス

*   **役割**: ワークスペースの準備、コードのチェックアウト、スクリプト実行、結果のコミット・プッシュ、後処理を一貫して行います。

#### 主なメソッド

*   `run_job(job: Dict, commit_info: Dict) -> None`: ジョブを実行します。
    *   `job`: 設定ファイルから読み込まれたジョブ定義。
    *   `commit_info`: トリガーとなったコミット情報。
*   `_prepare_workspace(job_name: str) -> str`: 作業用ディレクトリを作成・清掃します。
*   `_checkout_code(...) -> IVcsHandler`: リポジトリをクローン・チェックアウトします。
*   `_execute_script(...) -> None`: 定義されたスクリプトを実行します。
*   `_handle_result(...) -> None`: 変更がある場合、自動コミットとプッシュを行います。
*   `_cleanup_workspace(job_name: str) -> None`: 作業用ディレクトリを削除します。

## 2. JobTriggerService (`src/core/job_trigger.py`)

Webhookイベントに基づいて、どのジョブを実行すべきか判定するロジックを担当します。

### `JobTriggerService` クラス

*   **役割**: 設定ファイル (`config.yaml`) を読み込み、Webhookで通知された変更ファイルとジョブのトリガー条件（`trigger_paths`）を照合します。

#### 主なメソッド

*   `process_webhook_event(provider: WebhookProvider, payload: Dict, background_tasks: BackgroundTasks) -> List[str]`:
    *   ペイロードから変更ファイルリストを抽出します。
    *   設定ファイル内の全ジョブを走査し、条件に一致するジョブを実行します。
    *   `[skip ci]` がコミットメッセージに含まれる場合はスキップします。

## 3. WebhookHandler (`src/core/webhook_handler.py`)

異なるVCSプロバイダーからのWebhookリクエストを抽象化します。

### `WebhookProvider` (抽象基底クラス)

*   各プロバイダーはこれを継承して実装します。

### `GitHubProvider`

*   GitHub形式のWebhookペイロードを処理します。
*   `X-GitHub-Event` ヘッダーで判定されます。
*   `commits` 配列から `added`, `modified`, `removed` ファイルを抽出します。

### `WebhookProviderFactory`

*   リクエストヘッダーに基づいて適切なプロバイダーインスタンスを返します（Factory Pattern）。

## 4. VcsHandler (`src/core/vcs_handler.py`)

バージョン管理システム（現在はGit）の操作を抽象化します。

### `IVcsHandler` (抽象基底クラス)

*   VCS操作のインターフェースを定義します。

### `GitHandler`

*   `GitPython` ライブラリを使用してGit操作を行います。
*   **機能**:
    *   `prepare_repository`: リポジトリのクローン、ブランチのチェックアウト。アクセストークンの注入も行います。
    *   `has_changes`: 作業ディレクトリに変更があるか確認します。
    *   `commit_and_push`: 変更をコミットし、リモートにプッシュします。コミットメッセージには自動的に `[skip ci]` が付与され、無限ループを防ぎます。

## 5. JobExecutor (`src/core/job_executor.py`)

ジョブスクリプトの実行を抽象化します。

### `ShellJobExecutor`

*   シェルスクリプトを実行します。
*   `subprocess.run` を使用し、標準出力・標準エラー出力をキャプチャしてログに記録します。
*   実行に失敗（非ゼロ終了コード）した場合、例外を発生させます。

## 6. WorkspaceManager (`src/core/workspace_manager.py`)

ジョブ実行用の一時ディレクトリ（ワークスペース）の作成と削除を管理します。

*   `prepare_workspace`: ディレクトリが存在すれば削除し、新規作成します。
*   `cleanup_workspace`: ディレクトリを削除します。読み取り専用ファイルの削除にも対応しています。

## 7. ConfigLoader (`src/core/config_loader.py`)

設定ファイル (`config.yaml`) の読み込みを担当します。

*   環境変数の展開 (`${VAR}` 形式) をサポートしています。
*   デフォルトで `config.yaml` を読み込みますが、環境変数 `TOYCI_CONFIG_PATH` でパスを変更可能です。
