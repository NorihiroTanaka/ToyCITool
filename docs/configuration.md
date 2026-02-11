# 設定ファイルガイド (`config.yaml`)

ToyCI Serverの動作設定およびジョブ定義を行う `config.yaml` の仕様です。

## 基本構造

```yaml
server:
  host: "0.0.0.0"
  port: 8000

git:
  accessToken: "${GITHUB_TOKEN}"  # 環境変数から読み込み

jobs:
  - name: "example-job"
    repo_url: "https://github.com/user/repo.git"
    target_branch: "main"
    trigger_paths:
      - "src/"
      - "requirements.txt"
    script: |
      pip install -r requirements.txt
      python run_tests.py
```

## セクション詳細

### `server` セクション

サーバーの待ち受け設定です。

*   `host` (str): バインドアドレス（デフォルト: "0.0.0.0"）
*   `port` (int): ポート番号（デフォルト: 8000）

### `git` セクション

Git操作に関する設定です。

*   `accessToken` (str): リポジトリへの認証に使用するパーソナルアクセストークン。
    *   **重要**: セキュリティのため、直接記述せず環境変数 (`${ENV_VAR}`) を使用することを推奨します。

### `jobs` セクション

実行するCIジョブのリストです。各ジョブは以下のフィールドを持ちます。

*   `name` (str, 必須): ジョブの一意な名前。ログ出力などで使用されます。
*   `repo_url` (str, 必須): 対象のリポジトリURL（HTTPS）。
*   `target_branch` (str, 必須): チェックアウトおよびプッシュ対象のブランチ名。
*   `trigger_paths` (List[str], 任意): ジョブ実行のトリガーとなるファイルパスのパターン（前方一致）。
    *   指定されたパス以下のファイルに変更があった場合のみジョブが実行されます。
    *   省略した場合、常に実行される可能性があります（実装依存、通常は必須推奨）。
*   `script` (str, 必須): 実行するシェルスクリプト。
    *   複数行記述可能です。
    *   スクリプトが非ゼロの終了コードを返すとジョブは失敗とみなされます。

## 環境変数

設定ファイル内で `${VAR_NAME}` の形式で環境変数を参照できます。

例:
*   `accessToken: "${GITHUB_TOKEN}"` -> システムの環境変数 `GITHUB_TOKEN` の値に置換されます。
