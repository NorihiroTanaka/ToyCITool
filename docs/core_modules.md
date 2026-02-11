# コアモジュール詳細

`src/core/` ディレクトリに含まれる主要なモジュールの詳細説明です。

## 1. Config ([`src/core/config.py`](../src/core/config.py:1))

Pydanticベースの設定管理モジュールです。型安全な設定の読み込みと検証を提供します。

### `ServerConfig` クラス

サーバーの基本設定を管理します。

*   `host` (str): バインドアドレス（デフォルト: "0.0.0.0"）
*   `port` (int): ポート番号（デフォルト: 8000）
*   `workspace` (str): ワークスペースディレクトリ（デフォルト: "./workspace"）

### `GitConfig` クラス

Git操作に関する設定を管理します。

*   `repo_url` (Optional[str]): デフォルトのリポジトリURL
*   `accessToken` (Optional[str]): アクセストークン

### `JobConfig` クラス

個別のジョブ設定を管理します。

*   `name` (str, 必須): ジョブ名
*   `repo_url` (Optional[str]): リポジトリURL
*   `target_branch` (Optional[str]): ターゲットブランチ
*   `script` (str, 必須): 実行スクリプト
*   `watch_files` (List[str]): 監視ファイルパターン（glob形式）

### `Settings` クラス

アプリケーション全体の設定を管理します。

#### 主なメソッド

*   `load(config_path: Optional[str] = None) -> Settings`: 設定ファイルを読み込みます。
    *   `.env` ファイルから環境変数を自動読み込み（存在する場合）
    *   `config.yaml` を読み込み
    *   環境変数を展開（`${VAR}` 形式）
    *   Pydanticモデルとして検証

## 2. Container ([`src/core/container.py`](../src/core/container.py:1))

Dependency Injection コンテナです。シングルトンパターンで実装され、各サービスのインスタンスを一元管理します。

### `Container` クラス

*   **役割**: アプリケーション全体で使用されるサービスインスタンスを管理し、依存関係を解決します。

#### 主なプロパティ

*   `settings` -> `Settings`: 設定オブジェクトを取得します（遅延初期化）。
*   `job_service` -> `IJobService`: ジョブサービスのインスタンスを取得します。
*   `job_trigger_service` -> `JobTriggerService`: ジョブトリガーサービスのインスタンスを取得します。

#### 主なメソッド

*   `get_instance() -> Container`: シングルトンインスタンスを取得します。

### `get_container()` 関数

コンテナインスタンスを取得するヘルパー関数です。

## 3. Interfaces ([`src/core/interfaces.py`](../src/core/interfaces.py:1))

抽象インターフェースを定義するモジュールです。実装の詳細から分離し、テスタビリティを向上させます。

### `IJobExecutor` (抽象基底クラス)

ジョブ実行の抽象インターフェースです。

*   `execute(script: str, cwd: str) -> None`: スクリプトを実行します。

### `IVcsHandler` (抽象基底クラス)

VCS操作の抽象インターフェースです。

*   `prepare_repository(url: str, branch: str, access_token: Optional[str]) -> None`: リポジトリを準備します。
*   `has_changes() -> bool`: 変更があるか確認します。
*   `commit_and_push(message: str, branch: str) -> None`: コミットしてプッシュします。
*   `close() -> None`: リソースをクリーンアップします。

### `IJobService` (抽象基底クラス)

ジョブサービスの抽象インターフェースです。

*   `run_job(job_config: Dict[str, Any], commit_info: Dict[str, Any]) -> None`: ジョブを実行します。

### `IJobMatcher` (抽象基底クラス)

ジョブマッチングの抽象インターフェースです。

*   `match(job_config: Dict[str, Any], changed_files: Set[str]) -> bool`: ジョブを実行すべきか判定します。

### `WebhookProvider` (抽象基底クラス)

Webhookプロバイダーの抽象インターフェースです。

*   `get_provider_id() -> str`: プロバイダー識別子を取得します。
*   `should_skip(payload: Dict[str, Any]) -> bool`: 処理をスキップすべきか判定します。
*   `can_handle(headers: Dict[str, str]) -> bool`: リクエストを処理できるか判定します。
*   `extract_changed_files(payload: Dict[str, Any]) -> Set[str]`: 変更ファイルを抽出します。
*   `get_payload_meta(payload: Dict[str, Any]) -> Dict[str, Any]`: メタデータを抽出します。

## 4. JobMatcher ([`src/core/job_matcher.py`](../src/core/job_matcher.py:1))

ジョブの実行条件を判定するモジュールです。

### `JobMatcher` クラス

*   **役割**: 変更ファイルとジョブの監視パターンを照合し、ジョブを実行すべきか判定します。

#### 主なメソッド

*   `match(job_config: Dict[str, Any], changed_files: Set[str]) -> bool`: ジョブ設定と変更ファイルに基づき判定します。
*   `match_files(patterns: List[str], files: Set[str]) -> bool`: ファイルリストがパターンにマッチするか判定します。
    *   glob形式のパターンマッチング（`fnmatch`）を使用
    *   一つでもマッチすれば `True` を返す

## 5. JobService ([`src/core/job_service.py`](../src/core/job_service.py:1))

CIジョブの実行ライフサイクルを管理するサービスクラスです。

### `JobService` クラス

*   **役割**: ワークスペースの準備、コードのチェックアウト、スクリプト実行、結果のコミット・プッシュ、後処理を一貫して行います。

#### コンストラクタ

*   `__init__(settings: Settings, workspace_manager: Optional[WorkspaceManager], vcs_handler_cls: Type[IVcsHandler], job_executor_cls: Type[IJobExecutor])`: 依存関係を注入します。

#### 主なメソッド

*   `run_job(job_config: Dict[str, Any], commit_info: Dict[str, Any]) -> None`: ジョブを実行します。
    *   設定の補完（`job_config` になければ `settings.git` から取得）
    *   必須項目の検証（`repo_url`, `target_branch`, `script`）
*   `_prepare_workspace(job_name: str) -> str`: 作業用ディレクトリを作成・清掃します。
*   `_checkout_code(...) -> IVcsHandler`: リポジトリをクローン・チェックアウトします。
*   `_execute_script(...) -> None`: 定義されたスクリプトを実行します。
*   `_handle_result(...) -> None`: 変更がある場合、自動コミットとプッシュを行います。
*   `_cleanup_workspace(job_name: str) -> None`: 作業用ディレクトリを削除します（finally ブロックで必ず実行）。

## 6. JobTriggerService ([`src/core/job_trigger.py`](../src/core/job_trigger.py:1))

Webhookイベントに基づいて、どのジョブを実行すべきか判定するロジックを担当します。

### `JobTriggerService` クラス

*   **役割**: Webhookペイロードを解析し、変更ファイルとジョブのトリガー条件を照合します。

#### コンストラクタ

*   `__init__(settings: Settings, job_service: IJobService, job_matcher: Optional[IJobMatcher])`: 依存関係を注入します。

#### 主なメソッド

*   `process_webhook_event(provider: WebhookProvider, payload: Dict[str, Any], background_tasks: BackgroundTasks) -> List[str]`:
    *   プロバイダーの `should_skip()` でスキップ判定
    *   プロバイダーの `extract_changed_files()` で変更ファイルを抽出
    *   各ジョブに対して `JobMatcher.match()` で実行判定
    *   マッチしたジョブを `BackgroundTasks` に追加
    *   トリガーされたジョブ名のリストを返す

## 7. WebhookHandler ([`src/core/webhook_handler.py`](../src/core/webhook_handler.py:1))

異なるVCSプロバイダーからのWebhookリクエストを抽象化します。

### `GitHubProvider` クラス

*   **役割**: GitHub形式のWebhookペイロードを処理します。

#### 主なメソッド

*   `get_provider_id() -> str`: "github" を返します。
*   `should_skip(payload: Dict[str, Any]) -> bool`: コミットメッセージに `[ci skip]` または `ci skip` が含まれるか判定します。
*   `can_handle(headers: Dict[str, str]) -> bool`: `X-GitHub-Event` ヘッダーの存在を確認します（大文字小文字を無視）。
*   `extract_changed_files(payload: Dict[str, Any]) -> Set[str]`: `commits` 配列から `added`, `modified`, `removed` ファイルを抽出します。
*   `get_payload_meta(payload: Dict[str, Any]) -> Dict[str, Any]`: 最新のコミット情報を返します。

## 8. WebhookProviderFactory ([`src/core/webhook_factory.py`](../src/core/webhook_factory.py:1))

Webhookプロバイダーのファクトリクラスです。

### `WebhookProviderFactory` クラス

*   **役割**: リクエストヘッダーに基づいて適切なプロバイダーインスタンスを返します（Factory Pattern）。

#### クラス変数

*   `_providers`: 登録されたプロバイダーのリスト（現在は `GitHubProvider` のみ）

#### 主なメソッド

*   `get_provider(headers: Dict[str, str]) -> WebhookProvider`: 
    *   各プロバイダーの `can_handle()` を順に確認
    *   マッチしない場合はデフォルト（GitHub）にフォールバック

## 9. VcsHandler ([`src/core/vcs_handler.py`](../src/core/vcs_handler.py:1))

バージョン管理システム（現在はGit）の操作を抽象化します。

### `GitHandler` クラス

*   **役割**: `GitPython` ライブラリを使用してGit操作を行います。

#### 主なメソッド

*   `prepare_repository(url: str, branch: str, access_token: Optional[str]) -> None`: 
    *   リポジトリのクローン
    *   アクセストークンの注入（`vcs_utils.inject_auth_token()` を使用）
    *   ブランチのチェックアウト（存在しない場合は作成）
*   `has_changes() -> bool`: 作業ディレクトリに変更があるか確認します。
*   `commit_and_push(message: str, branch: str) -> None`: 
    *   変更をコミット
    *   リモートにプッシュ
    *   コミットメッセージに自動的に `[skip ci]` を付与（無限ループ防止）
*   `close() -> None`: リソースをクリーンアップします。

## 10. VcsUtils ([`src/core/vcs_utils.py`](../src/core/vcs_utils.py:1))

VCS関連のユーティリティ関数を提供します。

### 主な関数

*   `inject_auth_token(url: str, access_token: str) -> str`: 
    *   Git URLにアクセストークンを埋め込みます
    *   `https://github.com/user/repo.git` → `https://TOKEN@github.com/user/repo.git`
    *   http/https スキームのみサポート
*   `mask_auth_token(url: str, access_token: str) -> str`: 
    *   URLに含まれるアクセストークンをマスクします
    *   ログ出力時のセキュリティ対策

## 11. JobExecutor ([`src/core/job_executor.py`](../src/core/job_executor.py:1))

ジョブスクリプトの実行を抽象化します。

### `ShellJobExecutor` クラス

*   **役割**: シェルスクリプトを実行します。

#### 主なメソッド

*   `execute(script: str, cwd: str) -> None`: 
    *   `subprocess.run` を使用してスクリプトを実行
    *   標準出力・標準エラー出力をキャプチャしてログに記録
    *   実行に失敗（非ゼロ終了コード）した場合、例外を発生

## 12. WorkspaceManager ([`src/core/workspace_manager.py`](../src/core/workspace_manager.py:1))

ジョブ実行用の一時ディレクトリ（ワークスペース）の作成と削除を管理します。

### `WorkspaceManager` クラス

#### 主なメソッド

*   `prepare_workspace(job_name: str) -> str`: 
    *   ディレクトリが存在すれば削除
    *   新規作成
    *   ワークスペースパスを返す
*   `cleanup_workspace(job_name: str) -> None`: 
    *   ディレクトリを削除
    *   読み取り専用ファイルの削除にも対応（Windowsの `.git` ディレクトリ対策）

## 13. LoggingConfig ([`src/core/logging_config.py`](../src/core/logging_config.py:1))

ロギング設定を管理します。

### 主な関数

*   `setup_logging(config_path: str = "logging.yaml") -> None`: 
    *   `logging.yaml` からロギング設定を読み込み
    *   ログディレクトリの自動作成
    *   デフォルト設定へのフォールバック
