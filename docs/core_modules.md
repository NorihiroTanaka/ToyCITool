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
*   `access_token` (Optional[str]): アクセストークン（YAMLでは `accessToken` で記述）

### `DiscordNotificationConfig` / `NotificationsConfig` クラス

Discord通知の設定を管理します。

*   `discord.webhook_url` (str): Discord Webhook URL
*   `discord.on_success` (bool): 成功時に通知するか（デフォルト: true）
*   `discord.on_failure` (bool): 失敗時に通知するか（デフォルト: true）

### `BaseJobConfig` クラス

ジョブ設定の共通フィールドを定義します。

*   `name` (str, 必須): ジョブ名
*   `script` (str, 必須): 実行スクリプト
*   `watch_files` (List[str]): 監視ファイルパターン（glob形式）
*   `env` (Dict[str, str]): 追加の環境変数
*   `timeout` (Optional[int]): タイムアウト秒数
*   `venv` (Optional[str]): Python仮想環境のパス

### `JobConfig` クラス

`config.yaml` の `jobs` セクションで定義するジョブ設定です（`BaseJobConfig` を継承）。

*   `repo_url` (Optional[str]): リポジトリURL
*   `target_branch` (Optional[str]): ターゲットブランチ

### `RepoJobConfig` / `RepoCISettings` クラス

リポジトリ内 `.toyci.yaml` から読み込まれるジョブ設定です。`RepoJobConfig` は `BaseJobConfig` を継承します。
`repo_url` と `target_branch` はWebhookペイロードから自動補完されるため、`.toyci.yaml` には記述不要です。

### `Settings` クラス

アプリケーション全体の設定を管理します。

*   `server` (ServerConfig): サーバー設定
*   `git` (GitConfig): Git設定
*   `jobs` (List[JobConfig]): ジョブ一覧
*   `notifications` (Optional[NotificationsConfig]): 通知設定
*   `default_timeout` (int): デフォルトタイムアウト秒数（デフォルト: 3600）
*   `max_concurrent_jobs` (int): 同時実行数（デフォルト: 1）
*   `job_log_dir` (str): ジョブログ出力先（デフォルト: "log/jobs"）

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
*   `submit_job(job_config: Dict[str, Any], commit_info: Dict[str, Any]) -> None`: ジョブをキューに追加します。
*   `shutdown(wait: bool = True) -> None`: ワーカースレッドを停止します。

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
*   `extract_repo_info(payload: Dict[str, Any]) -> Optional[Dict[str, str]]`: リポジトリ情報（`repo_url`, `branch`）を抽出します。

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

CIジョブの実行ライフサイクルと内部ジョブキューを管理するサービスクラスです。

### `JobService` クラス

*   **役割**: ワークスペースの準備、コードのチェックアウト、スクリプト実行、結果のコミット・プッシュ、後処理を一貫して行います。内部ジョブキューとワーカースレッドでジョブを非同期処理します。

#### コンストラクタ

*   `__init__(settings: Settings, workspace_manager: Optional[WorkspaceManager], vcs_handler_cls: Type[IVcsHandler], job_executor_cls: Type[IJobExecutor])`: 依存関係を注入し、ワーカースレッドを起動します。

#### 主なメソッド

*   `submit_job(job_config: Dict[str, Any], commit_info: Dict[str, Any]) -> None`: ジョブをキューに追加します（非ブロッキング）。
*   `run_job(job_config: Dict[str, Any], commit_info: Dict[str, Any]) -> None`: ジョブを同期実行します（ワーカースレッドから呼び出し）。
    *   CI環境変数（`CI_JOB_ID`等）の構築
    *   設定の補完（`job_config` になければ `settings.git` から取得）
    *   必須項目の検証（`repo_url`, `target_branch`, `script`）
*   `shutdown(wait: bool = True) -> None`: ワーカースレッドを停止します。アプリケーションシャットダウン時に呼び出されます。
*   `_prepare_workspace(job_name: str) -> str`: 作業用ディレクトリを作成・清掃します。
*   `_checkout_code(...) -> IVcsHandler`: リポジトリをクローン・チェックアウトします。
*   `_execute_script(...) -> None`: 定義されたスクリプトを実行します（`env`, `timeout_seconds`, `venv` を渡す）。
*   `_handle_result(...) -> None`: 変更がある場合、自動コミットとプッシュを行います。
*   `_cleanup_workspace(job_name: str) -> None`: 作業用ディレクトリを削除します（finally ブロックで必ず実行）。
*   `_send_notification(...) -> None`: ジョブ完了後に通知を送信します。

## 6. JobTriggerService ([`src/core/job_trigger.py`](../src/core/job_trigger.py:1))

Webhookイベントに基づいて、どのジョブを実行すべきか判定するロジックを担当します。

### `JobTriggerService` クラス

*   **役割**: Webhookペイロードを解析し、変更ファイルとジョブのトリガー条件を照合します。ローカル設定とリポジトリ内CI設定の両方を処理します。

#### コンストラクタ

*   `__init__(settings: Settings, job_service: IJobService, job_matcher: Optional[IJobMatcher], repo_config_loader: Optional[RepoCIConfigLoader])`: 依存関係を注入します。

#### 主なメソッド

*   `process_webhook_event(provider: WebhookProvider, payload: Dict[str, Any]) -> List[str]`:
    *   プロバイダーの `should_skip()` でスキップ判定
    *   プロバイダーの `extract_changed_files()` で変更ファイルを抽出
    *   `config.yaml` の各ジョブに対して `JobMatcher.match()` で実行判定
    *   プロバイダーの `extract_repo_info()` でリポジトリ情報を取得
    *   `.toyci.yaml` の各ジョブに対しても同様に判定
    *   マッチしたジョブを `job_service.submit_job()` でキューに追加
    *   トリガーされたジョブ名のリストを返す

## 7. WebhookHandler ([`src/core/webhook_handler.py`](../src/core/webhook_handler.py:1))

異なるVCSプロバイダーからのWebhookリクエストを抽象化します。

### `GitHubProvider` クラス

*   **役割**: GitHub形式のWebhookペイロードを処理します。

#### 主なメソッド

*   `get_provider_id() -> str`: "github" を返します。
*   `should_skip(payload: Dict[str, Any]) -> bool`: コミットメッセージに `[skip ci]` または `skip ci` が含まれるか判定します。
*   `can_handle(headers: Dict[str, str]) -> bool`: `X-GitHub-Event` ヘッダーの存在を確認します（大文字小文字を無視）。
*   `extract_changed_files(payload: Dict[str, Any]) -> Set[str]`: `commits` 配列から `added`, `modified`, `removed` ファイルを抽出します。
*   `get_payload_meta(payload: Dict[str, Any]) -> Dict[str, Any]`: 最新のコミット情報を返します。
*   `extract_repo_info(payload: Dict[str, Any]) -> Optional[Dict[str, str]]`: `repository.clone_url` とブランチ（`ref` から `refs/heads/` を除去）を抽出します。

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

*   **役割**: シェルスクリプトをリアルタイムログ出力付きで実行します。

#### コンストラクタ

*   `__init__(job_log_dir: str = "log/jobs")`: ジョブログの出力先を指定します。

#### 主なメソッド

*   `execute(script: str, cwd: str, job_name: str, env: Optional[Dict[str, str]], timeout_seconds: Optional[int], venv: Optional[str]) -> None`: 
    *   `subprocess.Popen` を使用してスクリプトをリアルタイムに実行
    *   標準出力をジョブ別ログファイル（`log/jobs/{job_name}_{timestamp}.log`）とシステムログの両方に記録
    *   `venv` を指定した場合、仮想環境の `bin/Scripts` を PATH に優先追加
    *   タイムアウト発生時は `JobTimeoutError` を送出
    *   非ゼロ終了コードの場合は `ScriptExecutionError` を送出

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

## 14. Notifier ([`src/core/notifier.py`](../src/core/notifier.py:1))

ジョブの成功・失敗イベントを外部サービスに通知します。

### `NotificationEvent` クラス

通知イベントのデータを保持します。

*   `job_name` (str): ジョブ名
*   `success` (bool): 成功したか
*   `branch` (str): ブランチ名
*   `commit_hash` (str): コミットハッシュ
*   `commit_message` (Optional[str]): コミットメッセージ
*   `error_message` (Optional[str]): エラーメッセージ（失敗時）

### `Notifier` (抽象基底クラス)

通知の基底クラスです。

*   `notify(event: NotificationEvent) -> None`: 通知を送信します。

### `DiscordNotifier` クラス

Discord Webhookに通知を送信します。Embedでジョブ名・ブランチ・コミット・エラーを表示します。

### `CompositeNotifier` クラス

複数の通知先にまとめて送信するコンポジットクラスです。

### `NullNotifier` クラス

通知設定がない場合の何もしないノットファイアです。

### `build_notifier()` 関数

*   `build_notifier(notifications_config: Optional[Dict[str, Any]]) -> Notifier`: 設定から適切な `Notifier` を構築して返します。設定が空の場合は `NullNotifier` を返します。

## 15. RepoCIConfigLoader ([`src/core/repo_ci_config_loader.py`](../src/core/repo_ci_config_loader.py:1))

リポジトリ内の CI 設定ファイル (`.toyci.yaml`) を読み込むローダーです。

### `RepoCIConfigLoader` クラス

*   **役割**: リポジトリをシャロークローンして `.toyci.yaml` を読み込み、`RepoCISettings` として返します。

#### コンストラクタ

*   `__init__(access_token: Optional[str])`: Gitアクセストークンを設定します。

#### 主なメソッド

*   `load_from_repo(repo_url: str, branch: str) -> Optional[RepoCISettings]`:
    *   一時ディレクトリにリポジトリをクローン
    *   `.toyci.yaml` を読み込んで `RepoCISettings` を返す
    *   失敗した場合は `None` を返す（例外は発生させない）
*   `load_from_path(repo_path: str) -> Optional[RepoCISettings]`: クローン済みディレクトリから `.toyci.yaml` を読み込みます。

## 16. Exceptions ([`src/core/exceptions.py`](../src/core/exceptions.py:1))

ToyCIToolのカスタム例外を定義します。すべての例外は `ToyCIError` を基底クラスとします。

| 例外クラス | 説明 |
| --- | --- |
| `ToyCIError` | 全体の基底例外クラス |
| `ScriptExecutionError` | スクリプト実行失敗（`stdout`, `stderr`, `return_code` 属性あり） |
| `JobTimeoutError` | ジョブタイムアウト（`ScriptExecutionError` を継承、`timeout_seconds` 属性あり） |
| `RepositoryError` | VCS操作に関するエラー |
| `RepositoryNotInitializedError` | リポジトリが未初期化状態でのアクセスエラー |
| `WorkspaceError` | ワークスペース操作に関するエラー |
| `WorkspaceCleanupError` | ワークスペース削除失敗 |
| `JobValidationError` | ジョブ設定のバリデーションエラー |
| `WebhookPayloadError` | Webhookペイロードの解析エラー |
