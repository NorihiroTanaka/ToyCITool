# 設定ファイルガイド (`config.yaml`)

ToyCI Serverの動作設定およびジョブ定義を行う `config.yaml` の仕様です。

## 基本構造

```yaml
server:
  host: "0.0.0.0"
  port: 8000
  workspace: "workspace"

git:
  accessToken: "${GIT_ACCESS_TOKEN}"  # 環境変数から読み込み

jobs:
  - name: "example-job"
    repo_url: "https://github.com/user/repo.git"
    target_branch: "main"
    watch_files:
      - "src/*.py"
      - "requirements.txt"
      - "docs/**/*.md"
    script: |
      pip install -r requirements.txt
      python run_tests.py
```

## セクション詳細

### `server` セクション

サーバーの待ち受け設定です。

*   `host` (str, 任意): バインドアドレス（デフォルト: "0.0.0.0"）
*   `port` (int, 任意): ポート番号（デフォルト: 8000）
*   `workspace` (str, 任意): ジョブ実行用のワークスペースディレクトリ（デフォルト: "./workspace"）

**注意**: `host` と `port` はコマンドライン引数（`-a`, `-p`）で上書き可能です。

### `git` セクション

Git操作に関する設定です。

*   `accessToken` (str, 任意): リポジトリへの認証に使用するパーソナルアクセストークン。
    *   **重要**: セキュリティのため、直接記述せず環境変数 (`${ENV_VAR}`) を使用することを推奨します。
    *   各ジョブで個別に指定されていない場合のデフォルト値として使用されます。
*   `repo_url` (str, 任意): デフォルトのリポジトリURL（通常は各ジョブで指定）。

### `jobs` セクション

実行するCIジョブのリストです。各ジョブは以下のフィールドを持ちます。

*   `name` (str, 必須): ジョブの一意な名前。ログ出力やワークスペース管理で使用されます。
*   `repo_url` (str, 必須): 対象のリポジトリURL（HTTPS形式）。
    *   省略した場合、`git.repo_url` の値が使用されます（非推奨）。
*   `target_branch` (str, 必須): チェックアウトおよびプッシュ対象のブランチ名。
    *   ブランチが存在しない場合、自動的に作成されます。
*   `watch_files` (List[str], 必須): ジョブ実行のトリガーとなるファイルパスのパターン（glob形式）。
    *   指定されたパターンに一致するファイルに変更があった場合のみジョブが実行されます。
    *   **glob形式のパターンマッチング**をサポートしています（詳細は後述）。
    *   空リストの場合、ジョブは実行されません。
*   `script` (str, 必須): 実行するシェルスクリプトまたはコマンド。
    *   複数行記述可能です（YAML の `|` または `>` を使用）。
    *   スクリプトが非ゼロの終了コードを返すとジョブは失敗とみなされます。
    *   実行ディレクトリはクローンされたリポジトリのルートです。

## glob形式のパターンマッチング

`watch_files` では、Pythonの `fnmatch` モジュールによるglob形式のパターンマッチングがサポートされています。

### サポートされるパターン

| パターン | 説明 | 例 | マッチする例 |
| --- | --- | --- | --- |
| `*` | 任意の文字列（ディレクトリ区切りを除く） | `src/*.py` | `src/main.py`, `src/utils.py` |
| `**` | 任意の文字列（ディレクトリ区切りを含む）※ | `docs/**/*.md` | `docs/api.md`, `docs/guide/intro.md` |
| `?` | 任意の1文字 | `test?.py` | `test1.py`, `testA.py` |
| `[seq]` | 文字セット | `file[0-9].txt` | `file0.txt`, `file5.txt` |
| `[!seq]` | 文字セットの否定 | `file[!0-9].txt` | `fileA.txt`, `file_.txt` |

**※注意**: `fnmatch` は標準では `**` を特別扱いしませんが、パス全体に対してマッチングを行うため、実質的に再帰的なマッチングが可能です。

### パターン例

```yaml
watch_files:
  # 特定のファイル
  - "README.md"
  - "requirements.txt"
  
  # 特定のディレクトリ内の全ファイル
  - "src/*"
  
  # 特定の拡張子
  - "*.py"
  - "src/*.js"
  
  # 再帰的なマッチング
  - "src/**/*.py"      # src以下の全てのPythonファイル
  - "docs/**/*.md"     # docs以下の全てのMarkdownファイル
  
  # 複数の条件
  - "src/*.py"
  - "tests/*.py"
  - "config.yaml"
```

## 環境変数

設定ファイル内で `${VAR_NAME}` の形式で環境変数を参照できます。

### 環境変数の読み込み順序

1.  **システム環境変数**（最優先）
2.  **`.env` ファイル**（プロジェクトルートに配置）
3.  **デフォルト値**（設定ファイルで指定）

`.env` ファイルは起動時に自動的に読み込まれますが、既存のシステム環境変数は上書きされません。

### `.env` ファイルの例

```bash
# .env ファイル（プロジェクトルートに配置）
GIT_ACCESS_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
TOYCI_CONFIG_PATH=custom_config.yaml
```

### 設定ファイルでの参照例

```yaml
git:
  accessToken: "${GIT_ACCESS_TOKEN}"

jobs:
  - name: "my-job"
    repo_url: "${GIT_REPO_URL}"
    target_branch: "main"
    watch_files:
      - "src/*.py"
    script: "python build.py"
```

### 利用可能な環境変数

*   `TOYCI_CONFIG_PATH`: 設定ファイルのパスを指定します（デフォルト: `config.yaml`）。
*   `GIT_ACCESS_TOKEN`: Gitリポジトリへのアクセストークン（推奨）。
*   その他、任意の環境変数を `${VAR_NAME}` 形式で参照可能です。

## 設定例

### 基本的な設定

```yaml
server:
  host: "0.0.0.0"
  port: 8000
  workspace: "workspace"

git:
  accessToken: "${GIT_ACCESS_TOKEN}"

jobs:
  - name: "python-tests"
    repo_url: "https://github.com/user/python-project.git"
    target_branch: "main"
    watch_files:
      - "src/**/*.py"
      - "tests/**/*.py"
      - "requirements.txt"
    script: |
      pip install -r requirements.txt
      pytest tests/
```

### 複数ジョブの設定

```yaml
server:
  workspace: "workspace"

git:
  accessToken: "${GIT_ACCESS_TOKEN}"

jobs:
  - name: "frontend-build"
    repo_url: "https://github.com/user/frontend.git"
    target_branch: "build"
    watch_files:
      - "src/**/*.js"
      - "src/**/*.jsx"
      - "package.json"
    script: |
      npm install
      npm run build

  - name: "docs-generation"
    repo_url: "https://github.com/user/docs.git"
    target_branch: "gh-pages"
    watch_files:
      - "docs/**/*.md"
      - "mkdocs.yml"
    script: |
      pip install mkdocs
      mkdocs build
      cp -r site/* .

  - name: "python-linting"
    repo_url: "https://github.com/user/python-project.git"
    target_branch: "lint-fixes"
    watch_files:
      - "**/*.py"
    script: |
      pip install black flake8
      black .
      flake8 .
```

### Windows環境での設定

```yaml
server:
  workspace: "workspace"

git:
  accessToken: "${GIT_ACCESS_TOKEN}"

jobs:
  - name: "windows-build"
    repo_url: "https://github.com/user/project.git"
    target_branch: "main"
    watch_files:
      - "src/**/*.py"
    script: |
      python -m pip install -r requirements.txt
      python build.py
```

## ベストプラクティス

1.  **環境変数の使用**: アクセストークンなどの機密情報は必ず環境変数を使用してください。
2.  **`.env` ファイルの管理**: `.env` ファイルは `.gitignore` に含め、Gitで管理しないでください。
3.  **パターンの最適化**: `watch_files` は必要最小限のパターンに絞ることで、不要なジョブ実行を防げます。
4.  **スクリプトのテスト**: `script` は事前にローカル環境でテストしてから設定してください。
5.  **ブランチ戦略**: `target_branch` は専用のブランチ（例: `ci-output`, `build`）を使用することを推奨します。
6.  **ワークスペースの管理**: `server.workspace` は十分なディスク容量がある場所を指定してください。

## トラブルシューティング

### ジョブが実行されない

*   `watch_files` のパターンが変更ファイルにマッチしているか確認してください。
*   ログで「スキップされました」というメッセージを確認してください。
*   コミットメッセージに `[ci skip]` または `ci skip` が含まれていないか確認してください。

### 認証エラー

*   `GIT_ACCESS_TOKEN` が正しく設定されているか確認してください。
*   トークンに必要な権限（repo）が付与されているか確認してください。
*   `.env` ファイルが正しく読み込まれているか確認してください。

### スクリプト実行エラー

*   スクリプトの実行権限を確認してください。
*   スクリプト内のパスが相対パスで正しく指定されているか確認してください。
*   ログで詳細なエラーメッセージを確認してください。
