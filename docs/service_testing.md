# Windowsサービス動作テストガイド

このドキュメントでは、ToyCIToolをWindowsサービスとして実行する前後のテスト手順を説明します。

## 目次

1. [テストの概要](#テストの概要)
2. [事前準備](#事前準備)
3. [ローカル実行でのテスト](#ローカル実行でのテスト)
4. [サービスとしての動作テスト](#サービスとしての動作テスト)
5. [Git認証のテスト](#git認証のテスト)
6. [統合テスト](#統合テスト)
7. [チェックリスト](#チェックリスト)

---

## テストの概要

Windowsサービスとして実行する前に、以下の項目を順番にテストします：

1. ✅ ローカル環境での正常動作
2. ✅ Git認証情報の動作確認
3. ✅ サービスとしての起動・停止
4. ✅ WebHook受信とジョブ実行
5. ✅ Git push機能

---

## 事前準備

### 1. 環境の確認

```cmd
# Pythonのバージョン確認
python --version

# Gitのバージョン確認
git --version

# 依存ライブラリの確認
pip list | findstr "fastapi uvicorn GitPython pydantic"
```

### 2. 設定ファイルの準備

#### config.yaml

```yaml
server:
  workspace: "workspace"

git:
  accessToken: ${GIT_ACCESS_TOKEN}

jobs:
  - name: "TestJob"
    repo_url: ${GIT_REPO_URL}
    watch_files:
      - "*.txt"
      - "*.md"
    script: "echo Test > output.txt"
    target_branch: "test-output"
```

#### .env（ローカルテスト用）

```
GIT_ACCESS_TOKEN=your_actual_token_here
GIT_REPO_URL=http://localhost:3000/test_user/test_repo.git
```

#### ToyCITool.xml（サービステスト用）

```xml
<env name="GIT_ACCESS_TOKEN" value="your_actual_token_here"/>
<env name="GIT_REPO_URL" value="http://localhost:3000/test_user/test_repo.git"/>
```

### 3. テスト用リポジトリの準備

Gitサーバー（GitHub、GitLab、Giteaなど）にテスト用リポジトリを作成：

1. リポジトリ名: `test_repo`
2. ブランチ: `main`
3. ファイル: `README.md`（任意の内容）
4. WebHook設定: `http://localhost:8000/webhook`

---

## ローカル実行でのテスト

サービスとして登録する前に、通常のPythonプログラムとして動作確認します。

### テスト1: 基本起動テスト

**目的**: アプリケーションが正常に起動するか確認

```cmd
cd /d f:\Project\ToyCITool
python -m src.main
```

**期待される結果**:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**確認項目**:
- ✅ エラーなく起動する
- ✅ ポート8000でリッスンしている
- ✅ ログファイルが `log/` ディレクトリに作成される

### テスト2: 設定ファイルの読み込みテスト

**目的**: 環境変数と設定ファイルが正しく読み込まれるか確認

別のターミナルで：

```cmd
curl http://localhost:8000/
```

または、ブラウザで `http://localhost:8000/` にアクセス

**期待される結果**:
```json
{"message":"ToyCITool is running"}
```

**確認項目**:
- ✅ APIが応答する
- ✅ ログに設定読み込みのメッセージが記録される

### テスト3: WebHook受信テスト

**目的**: WebHookを受信して処理できるか確認

テスト用のWebHookペイロードを送信：

```powershell
# PowerShellで実行
$body = @{
    ref = "refs/heads/main"
    commits = @(
        @{
            id = "test123"
            added = @()
            modified = @("README.md")
            removed = @()
        }
    )
    repository = @{
        clone_url = $env:GIT_REPO_URL
    }
} | ConvertTo-Json -Depth 10

Invoke-WebRequest -Uri "http://localhost:8000/webhook" `
    -Method POST `
    -Headers @{"Content-Type"="application/json"; "x-github-event"="push"} `
    -Body $body
```

または、curlで：

```cmd
curl -X POST http://localhost:8000/webhook ^
  -H "Content-Type: application/json" ^
  -H "x-github-event: push" ^
  -d "{\"ref\":\"refs/heads/main\",\"commits\":[{\"id\":\"test123\",\"modified\":[\"README.md\"]}],\"repository\":{\"clone_url\":\"http://localhost:3000/test_user/test_repo.git\"}}"
```

**期待される結果**:
```json
{"status":"success","message":"Webhook processed"}
```

**確認項目**:
- ✅ WebHookが受信される
- ✅ ジョブがマッチする（`README.md`が監視対象の場合）
- ✅ ログにジョブ実行のメッセージが記録される

---

## サービスとしての動作テスト

### テスト4: サービスのインストールと起動

**目的**: Windowsサービスとして正常に起動するか確認

```cmd
# 管理者権限でコマンドプロンプトを開く
cd /d f:\Project\ToyCITool

# サービスをインストール
ToyCITool.exe install

# サービスを起動
ToyCITool.exe start

# 状態を確認
ToyCITool.exe status
```

**期待される結果**:
```
Service 'ToyCITool' was installed successfully.
Service 'ToyCITool' started successfully.
Status: Running
```

**確認項目**:
- ✅ サービスがインストールされる
- ✅ サービスが起動する
- ✅ `services.msc` でサービスが「実行中」と表示される

### テスト5: サービスログの確認

**目的**: サービスとして実行時にログが正しく出力されるか確認

```cmd
# 標準出力ログを確認
type ToyCITool.out.log

# エラーログを確認
type ToyCITool.err.log

# WinSWのログを確認
type ToyCITool.wrapper.log
```

**期待される結果**:
- `ToyCITool.out.log` にアプリケーションの起動メッセージが記録される
- `ToyCITool.err.log` にエラーがない（または警告のみ）
- `ToyCITool.wrapper.log` にサービス起動のメッセージが記録される

**確認項目**:
- ✅ ログファイルが作成される
- ✅ 起動メッセージが記録される
- ✅ エラーがない

### テスト6: サービスの停止と再起動

**目的**: サービスの停止・再起動が正常に動作するか確認

```cmd
# サービスを停止
ToyCITool.exe stop

# 状態を確認
ToyCITool.exe status

# サービスを再起動
ToyCITool.exe restart

# 状態を確認
ToyCITool.exe status
```

**期待される結果**:
- 停止後: `Status: Stopped`
- 再起動後: `Status: Running`

**確認項目**:
- ✅ サービスが正常に停止する
- ✅ サービスが正常に再起動する
- ✅ 再起動後もAPIが応答する

---

## Git認証のテスト

### テスト7: 環境変数の確認

**目的**: サービス実行時に環境変数が正しく設定されているか確認

テスト用のスクリプトを作成：

**test_env.py**:
```python
import os
import sys

token = os.environ.get('GIT_ACCESS_TOKEN')
repo_url = os.environ.get('GIT_REPO_URL')

print(f"GIT_ACCESS_TOKEN: {'SET' if token else 'NOT SET'}")
print(f"GIT_REPO_URL: {repo_url if repo_url else 'NOT SET'}")

sys.exit(0 if token else 1)
```

`config.yaml` を一時的に変更：
```yaml
jobs:
  - name: "EnvTest"
    repo_url: ${GIT_REPO_URL}
    watch_files:
      - "*.txt"
    script: "python test_env.py"
    target_branch: "test"
```

WebHookを送信してジョブを実行し、ログを確認。

**期待される結果**:
```
GIT_ACCESS_TOKEN: SET
GIT_REPO_URL: http://localhost:3000/test_user/test_repo.git
```

**確認項目**:
- ✅ `GIT_ACCESS_TOKEN` が設定されている
- ✅ `GIT_REPO_URL` が設定されている

### テスト8: Git clone テスト

**目的**: 認証情報を使用してリポジトリをcloneできるか確認

WebHookを送信してジョブを実行し、ログを確認：

```cmd
# ログディレクトリを確認
dir log

# 最新のログファイルを確認
type log\app.log
```

**期待される結果**（ログ内）:
```
[TestJob] ワークスペースを準備中...
[TestJob] リポジトリを準備中: http://localhost:3000/test_user/test_repo.git (test-output)
アクセストークンを使用して http://*****@localhost:3000/test_user/test_repo.git をクローンしています...
Remote URL を認証付きURLに設定しました
```

**確認項目**:
- ✅ リポジトリがcloneされる
- ✅ アクセストークンがマスクされている（`*****`）
- ✅ remote URLが認証付きに設定される

### テスト9: Git push テスト

**目的**: 認証情報を使用してリポジトリにpushできるか確認

ジョブのスクリプトで実際にファイルを変更：

```yaml
jobs:
  - name: "PushTest"
    repo_url: ${GIT_REPO_URL}
    watch_files:
      - "*.md"
    script: "echo Test Output > output.txt"
    target_branch: "test-output"
```

WebHookを送信してジョブを実行。

**期待される結果**（ログ内）:
```
[PushTest] スクリプトを実行中: echo Test Output > output.txt
[PushTest] スクリプトが正常に終了しました。
[PushTest] 変更が検出されました。test-output へプッシュします...
Push前にremote URLを認証付きURLに更新しました
[PushTest] test-output へ変更をプッシュしています...
[PushTest] プッシュ成功。
```

Gitサーバーで `test-output` ブランチを確認し、`output.txt` が追加されていることを確認。

**確認項目**:
- ✅ ファイルが変更される
- ✅ 変更が検出される
- ✅ コミットが作成される
- ✅ pushが成功する
- ✅ リモートリポジトリに変更が反映される

---

## 統合テスト

### テスト10: エンドツーエンドテスト

**目的**: 実際のワークフローが正常に動作するか確認

**シナリオ**:
1. Gitリポジトリの `main` ブランチで `README.md` を編集
2. コミットしてpush
3. WebHookが自動的に送信される
4. ToyCIToolがWebHookを受信
5. ジョブが実行される
6. 結果が `test-output` ブランチにpushされる

**手順**:

1. **リポジトリを編集**:
   ```cmd
   git clone http://localhost:3000/test_user/test_repo.git
   cd test_repo
   echo "Updated" >> README.md
   git add README.md
   git commit -m "Update README"
   git push origin main
   ```

2. **ToyCIToolのログを監視**:
   ```cmd
   # PowerShellで
   Get-Content f:\Project\ToyCITool\ToyCITool.out.log -Wait -Tail 50
   ```

3. **結果を確認**:
   ```cmd
   git fetch origin
   git checkout test-output
   dir
   type output.txt
   ```

**期待される結果**:
- ✅ WebHookが受信される
- ✅ ジョブが実行される
- ✅ `test-output` ブランチに変更がpushされる
- ✅ `output.txt` が作成される

**確認項目**:
- ✅ 全体のワークフローが正常に動作する
- ✅ エラーが発生しない
- ✅ ログに異常なメッセージがない

---

## チェックリスト

### ローカル実行テスト

- [ ] アプリケーションが起動する
- [ ] 設定ファイルが読み込まれる
- [ ] 環境変数が展開される
- [ ] WebHookを受信できる
- [ ] ジョブがマッチする
- [ ] スクリプトが実行される

### サービス実行テスト

- [ ] サービスがインストールされる
- [ ] サービスが起動する
- [ ] ログファイルが作成される
- [ ] サービスが停止・再起動できる
- [ ] 環境変数が設定される（WinSW経由）

### Git認証テスト

- [ ] アクセストークンが設定される
- [ ] リポジトリがcloneされる
- [ ] remote URLが認証付きに設定される
- [ ] 変更がコミットされる
- [ ] 変更がpushされる
- [ ] リモートリポジトリに反映される

### 統合テスト

- [ ] WebHookが自動的に送信される
- [ ] ジョブが自動的に実行される
- [ ] 結果が自動的にpushされる
- [ ] エラーが発生しない

### セキュリティテスト

- [ ] アクセストークンがログにマスクされる
- [ ] 設定ファイルのアクセス権限が適切
- [ ] サービスアカウントの権限が最小限

---

## トラブルシューティング

### テストが失敗した場合

1. **ログを確認**:
   ```cmd
   type ToyCITool.out.log
   type ToyCITool.err.log
   type log\app.log
   ```

2. **環境変数を確認**:
   - `ToyCITool.xml` の `<env>` タグを確認
   - サービスを再起動

3. **手動でGit操作をテスト**:
   ```cmd
   cd workspace\TestJob
   git remote -v
   git push origin test-output
   ```

4. **詳細なログを有効化**:
   `logging.yaml` でログレベルを `DEBUG` に変更

5. **サービスを再インストール**:
   ```cmd
   ToyCITool.exe uninstall
   ToyCITool.exe install
   ToyCITool.exe start
   ```

---

## まとめ

このテストガイドに従うことで、ToyCIToolがWindowsサービスとして正常に動作することを確認できます。

**重要なポイント**:
1. ✅ ローカル実行で動作確認してからサービス化
2. ✅ 各機能を段階的にテスト
3. ✅ ログを常に確認
4. ✅ Git認証を重点的にテスト
5. ✅ エンドツーエンドで動作確認

すべてのテストが成功したら、本番環境でのサービス運用を開始できます。
