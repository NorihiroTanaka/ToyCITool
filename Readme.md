# 簡易的なCIツール

オンプレミスで構築したGitサーバーやGitHubからのWebHookをトリガーとして動作する、軽量なCIツールです。
変更されたファイルを検知し、指定されたスクリプトを実行した後、その結果（変更されたファイルなど）を自動的に指定ブランチへプッシュします。

## 機能

- **WebHook連携**: GitHub形式のWebHook (JSONペイロード) を受け取り、CIプロセスを開始します。
    - `x-github-event` ヘッダーによるGitHubイベントの自動判別に対応しています。
    - その他のプロバイダーの場合も、デフォルトでGitHub互換として処理を試みます。
- **ファイル監視**: WebHookペイロードに含まれる変更ファイル（追加・変更・削除）を抽出し、設定ファイルで指定したパターン（ワイルドカード対応）に一致する場合のみジョブを実行します。
- **スクリプト実行**: 条件に一致した場合、任意のシェルスクリプトを実行します。
    - **タイムアウト制御**: ジョブごとまたはグローバルでタイムアウトを設定できます。
    - **Python venvサポート**: 仮想環境を指定してスクリプトを実行できます。
    - **カスタム環境変数**: ジョブごとに環境変数を設定できます。
    - **CI環境変数**: `CI_JOB_ID`、`CI_COMMIT_HASH`、`CI_BRANCH` 等の変数が自動的に注入されます。
    - **ジョブログ**: ジョブごとのログが `log/jobs/` に保存されます。
- **自動Push**: スクリプト実行によってワークスペース内で発生した変更を検知し、自動的に指定されたターゲットブランチへコミット＆プッシュします。
    - ターゲットブランチが存在しない場合、リモートから取得するか、新規に作成します。
- **リポジトリ内CI設定**: トリガーされたリポジトリ内の `.toyci.yaml` を参照し、ジョブを実行できます。
    - CI設定をCIサーバーではなく各リポジトリで管理できます。
- **ジョブキュー**: 内部スレッドプールでジョブを管理します。`max_concurrent_jobs` で同時実行数を制御できます。
- **Discord通知**: ジョブの成功・失敗をDiscord Webhookで通知できます。
- **Windowsサービス対応**: WinSWを使用してWindowsサービスとして実行可能です。
    - システム起動時の自動起動
    - バックグラウンド実行
    - サービスとしての管理（停止・再起動など）

## 必要要件

- Python 3.x
- Git

## インストールと起動

1. 依存ライブラリのインストール
   ```bash
   pip install -r requirements.txt
   ```

2. 環境変数の設定（オプション）
   
   `.env`ファイルを使用して環境変数を設定できます。
   
   ```bash
   # .env_templateをコピーして.envを作成
   copy .env_template .env  # Windows
   # または
   cp .env_template .env    # Linux/Mac
   ```
   
   `.env`ファイルを編集して必要な環境変数を設定します：
   ```
   GIT_ACCESS_TOKEN=your_token_here
   ```
   
   **注意**: `.env`ファイルはGitで管理されません（`.gitignore`に含まれています）。

3. サーバーの起動
   
   推奨される起動方法は `src.main` モジュールを使用する方法です。これにより、コマンドライン引数での設定が可能になります。

   ```bash
   python -m src.main
   ```

   **オプション:**
   - `-a`, `--address`: バインドするホストアドレスを指定します（デフォルト: 設定ファイルの値 または `0.0.0.0`）。
   - `-p`, `--port`: バインドするポート番号を指定します（デフォルト: 設定ファイルの値 または `8000`）。
   - `--print-default-config`: デフォルトの設定値をYAML形式で標準出力し、サーバーを起動せずに終了します。

   例:
   ```bash
   python -m src.main --port 8080
   ```

   また、開発用として直接 `uvicorn` コマンドで起動することも可能です（ただし、CLI引数による設定オーバーライドは機能しません）。
   ```bash
   uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload
   ```

## 設定 (config.yaml)

プロジェクトルートに `config.yaml` を配置してください。
環境変数 `TOYCI_CONFIG_PATH` で設定ファイルのパスを変更することも可能です。

```yaml
server:
  host: "0.0.0.0"
  port: 8000
  workspace: "workspace"

git:
  accessToken: "${GIT_ACCESS_TOKEN}"

# ジョブの同時実行数とタイムアウト（秒）
max_concurrent_jobs: 1
default_timeout: 3600
job_log_dir: "log/jobs"

# Discord通知（オプション）
notifications:
  discord:
    webhook_url: "${DISCORD_WEBHOOK_URL}"
    on_success: true
    on_failure: true

jobs:
  - name: "Example Build"
    repo_url: "https://github.com/example/repo.git"  # CI対象のリポジトリURL
    watch_files:
      - "src/*.py"       # 監視するファイルパターン (glob形式)
      - "requirements.txt"
    script: "./scripts/build.sh"       # 実行するスクリプト
    target_branch: "build-output"      # 変更をプッシュするブランチ名
    timeout: 600                       # タイムアウト秒数（オプション）
    venv: ".venv"                      # Python仮想環境パス（オプション）
    env:                               # 追加の環境変数（オプション）
      MY_VAR: "value"
```

### 設定項目

| 項目 | 説明 |
| --- | --- |
| `server.host` | サーバーのホストアドレス (デフォルト: 0.0.0.0) |
| `server.port` | サーバーのポート番号 (デフォルト: 8000) |
| `server.workspace` | ジョブ実行用のワークスペースディレクトリ (デフォルト: ./workspace) |
| `git.accessToken` | Gitリポジトリへのアクセストークン（環境変数参照推奨） |
| `max_concurrent_jobs` | ジョブの同時実行数 (デフォルト: 1) |
| `default_timeout` | デフォルトのジョブタイムアウト秒数 (デフォルト: 3600) |
| `job_log_dir` | ジョブログの出力先ディレクトリ (デフォルト: log/jobs) |
| `notifications.discord.webhook_url` | Discord通知先のWebhook URL |
| `notifications.discord.on_success` | 成功時に通知するか (デフォルト: true) |
| `notifications.discord.on_failure` | 失敗時に通知するか (デフォルト: true) |
| `jobs` | 実行するジョブのリスト |
| `jobs[].name` | ジョブの識別名 |
| `jobs[].repo_url` | CI対象のリポジトリURL |
| `jobs[].watch_files` | 変更を検知するファイルパターンのリスト |
| `jobs[].script` | 実行するコマンドまたはスクリプトパス |
| `jobs[].target_branch` | スクリプト実行後の変更をPushする先のブランチ名 |
| `jobs[].timeout` | このジョブのタイムアウト秒数（省略時は `default_timeout` を使用） |
| `jobs[].venv` | Python仮想環境のパス（省略可） |
| `jobs[].env` | ジョブに追加する環境変数のマップ（省略可） |

## リポジトリ内CI設定 (.toyci.yaml)

CI設定をCIサーバー側の `config.yaml` だけでなく、各リポジトリ内の `.toyci.yaml` ファイルに記述できます。
WebHookを受信すると、トリガーされたリポジトリをシャロークローンして `.toyci.yaml` を読み込み、定義されたジョブを実行します。

```yaml
# .toyci.yaml（リポジトリルートに配置）
jobs:
  - name: "test"
    watch_files:
      - "src/**/*.py"
      - "tests/**/*.py"
    script: |
      pip install -r requirements.txt
      pytest
```

`repo_url` と `target_branch` はWebHookペイロードから自動補完されます。

## CI環境変数

スクリプト実行時に以下の環境変数が自動的に注入されます。

| 変数名 | 内容 |
| --- | --- |
| `CI_JOB_ID` | ジョブID（ジョブ名 + ランダムサフィックス） |
| `CI_COMMIT_HASH` | トリガーとなったコミットのハッシュ |
| `CI_BRANCH` | ブランチ名 |
| `CI_REPO_URL` | リポジトリURL |
| `CI_WORKSPACE` | ワークスペースの絶対パス |

## 使い方

1. `config.yaml` を作成し、リポジトリや監視設定を記述します。
2. CIサーバーを起動します。
3. Gitサーバー（GitHubやGitLab、Giteaなど）のWebHook設定で、このサーバーのURL (`http://<your-server>:8000/webhook`) を登録します。
    - Content Type は `application/json` を選択してください。
4. 監視対象のファイルを変更してPushすると、自動的にスクリプトが実行され、結果が指定ブランチにPushされます。

## Windowsサービスとしての実行

ToyCIToolをWindowsサービスとして実行することで、システム起動時の自動起動やバックグラウンド実行が可能になります。

### クイックスタート

1. **WinSWのダウンロード**
   - [WinSWのリリースページ](https://github.com/winsw/winsw/releases)から `WinSW-x64.exe` をダウンロード
   - `ToyCITool.exe` にリネームしてプロジェクトルートに配置

2. **設定ファイルの編集**
   - `ToyCITool.xml` を編集
   - Pythonのパス、作業ディレクトリ、Gitアクセストークンを設定

3. **サービスの登録と起動**
   ```cmd
   # 管理者権限でコマンドプロンプトを開く
   cd /d f:\Project\ToyCITool
   ToyCITool.exe install
   ToyCITool.exe start
   ```

### 詳細なドキュメント

- **[Windowsサービス実行ガイド](docs/windows_service.md)**: WinSWのインストール、設定、トラブルシューティング
- **[テスト手順書](docs/service_testing.md)**: サービス化前後のテスト方法

### 重要な注意事項

Windowsサービスとして実行する場合、以下の点に注意してください：

1. **環境変数の設定**: `.env` ファイルは使用されません。`ToyCITool.xml` で環境変数を設定してください。
   ```xml
   <env name="GIT_ACCESS_TOKEN" value="your_token_here"/>
   ```

2. **Git認証**: Git Credential Managerは使用できません。アクセストークンを明示的に設定する必要があります。

3. **作業ディレクトリ**: 絶対パスで指定してください。

詳細は [docs/windows_service.md](docs/windows_service.md) を参照してください。

## 環境変数

### .envファイルによる設定

プロジェクトルートに`.env`ファイルを配置することで、環境変数を設定できます。
`.env`ファイルは起動時に自動的に読み込まれ、システムの環境変数として登録されます。

**優先順位**:
1. システム環境変数（最優先）
2. `.env`ファイルの値
3. デフォルト値

**例**: `.env`ファイル
```
GIT_ACCESS_TOKEN=your_github_token_here
TOYCI_CONFIG_PATH=custom_config.yaml
```

これにより、`config.yaml`内で`${GIT_ACCESS_TOKEN}`のように環境変数を参照できます：
```yaml
git:
  accessToken: ${GIT_ACCESS_TOKEN}
```

### 利用可能な環境変数

- `TOYCI_CONFIG_PATH`: 設定ファイルのパスを指定します（デフォルト: `config.yaml`）。
- `GIT_ACCESS_TOKEN`: Gitリポジトリへのアクセストークン（config.yamlで参照可能）。
