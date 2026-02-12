# Windowsサービスとしての実行ガイド

このドキュメントでは、ToyCIToolをWindowsサービスとして実行する方法について説明します。

## 目次

1. [概要](#概要)
2. [前提条件](#前提条件)
3. [WinSWのインストール](#winswのインストール)
4. [設定ファイルの準備](#設定ファイルの準備)
5. [サービスの登録と起動](#サービスの登録と起動)
6. [サービスの管理](#サービスの管理)
7. [トラブルシューティング](#トラブルシューティング)
8. [セキュリティに関する注意事項](#セキュリティに関する注意事項)

---

## 概要

ToyCIToolをWindowsサービスとして実行することで、以下のメリットがあります：

- **自動起動**: システム起動時に自動的にサービスが開始されます
- **バックグラウンド実行**: ユーザーがログアウトしても動作し続けます
- **安定性**: サービスとして管理されるため、障害時の自動再起動が可能です

### Windowsサービス実行時の特殊な考慮事項

Windowsサービスは通常のユーザーセッションとは異なる環境で実行されるため、以下の点に注意が必要です：

- **環境変数**: `.env`ファイルが読み込まれない可能性があるため、WinSW設定ファイルで明示的に設定
- **認証情報**: Git Credential Managerにアクセスできないため、アクセストークンを明示的に設定
- **作業ディレクトリ**: 絶対パスで指定する必要があります

---

## 前提条件

以下がインストールされていることを確認してください：

1. **Python 3.x**
   - コマンドプロンプトで `python --version` を実行して確認
   - Pythonのインストールパスを確認（例: `C:\Python311\python.exe`）

2. **Git**
   - コマンドプロンプトで `git --version` を実行して確認

3. **ToyCIToolの依存ライブラリ**
   ```cmd
   pip install -r requirements.txt
   ```

4. **管理者権限**
   - サービスの登録には管理者権限が必要です

---

## WinSWのインストール

WinSW (Windows Service Wrapper) は、任意のプログラムをWindowsサービスとして実行するためのツールです。

### ステップ1: WinSWのダウンロード

1. [WinSWのGitHubリリースページ](https://github.com/winsw/winsw/releases)にアクセス
2. 最新版の `WinSW-x64.exe` をダウンロード（64bit Windowsの場合）
3. ダウンロードしたファイルを `ToyCITool.exe` にリネーム
4. ToyCIToolプロジェクトのルートディレクトリに配置

```
f:\Project\ToyCITool\
├── ToyCITool.exe          ← WinSWの実行ファイル（リネーム後）
├── ToyCITool.xml          ← 設定ファイル
├── config.yaml
├── src\
└── ...
```

### ステップ2: ファイル配置の確認

プロジェクトルートに以下のファイルが配置されていることを確認：

- `ToyCITool.exe` (WinSWの実行ファイル)
- `ToyCITool.xml` (WinSW設定ファイル)

**重要**: ファイル名の拡張子を除いた部分（`ToyCITool`）は一致している必要があります。

---

## 設定ファイルの準備

### ステップ1: ToyCITool.xmlの編集

プロジェクトルートにある `ToyCITool.xml` を編集します。

#### 必須の変更項目

1. **Pythonの実行パス**
   ```xml
   <executable>C:\Python311\python.exe</executable>
   ```
   
   Pythonのインストールパスを確認するには：
   ```cmd
   where python
   ```

2. **作業ディレクトリ**
   ```xml
   <workingdirectory>f:\Project\ToyCITool</workingdirectory>
   ```
   
   ToyCIToolプロジェクトのルートディレクトリの絶対パスを指定します。

3. **Gitアクセストークン**
   ```xml
   <env name="GIT_ACCESS_TOKEN" value="your_actual_token_here"/>
   ```
   
   実際のGitアクセストークンに置き換えます。
   
   **トークンの取得方法**:
   - **GitHub**: Settings → Developer settings → Personal access tokens → Generate new token (repo権限)
   - **GitLab**: User Settings → Access Tokens → Add new token (api権限)
   - **Gitea**: Settings → Applications → Generate New Token (write:repository権限)

#### オプションの変更項目

1. **サービス起動モード**
   ```xml
   <startmode>Automatic</startmode>
   ```
   - `Automatic`: システム起動時に自動起動
   - `Manual`: 手動起動のみ

2. **ログ設定**
   ```xml
   <log mode="roll-by-size">
     <sizeThreshold>10240</sizeThreshold>  <!-- 10MB -->
     <keepFiles>8</keepFiles>
   </log>
   ```

3. **サービスアカウント**（デフォルトはLOCAL SYSTEMアカウント）
   ```xml
   <serviceaccount>
     <domain>DOMAIN</domain>
     <user>username</user>
     <password>password</password>
     <allowservicelogon>true</allowservicelogon>
   </serviceaccount>
   ```

### ステップ2: config.yamlの確認

`config.yaml` が正しく設定されていることを確認します：

```yaml
server:
  workspace: "workspace"

git:
  accessToken: ${GIT_ACCESS_TOKEN}  # 環境変数から読み込み

jobs:
  - name: "Example"
    repo_url: ${GIT_REPO_URL}
    watch_files:
      - "src/*.py"
      - "requirements.txt"
    script: "scripts\\build.cmd"
    target_branch: "main"
```

**注意**: `${GIT_ACCESS_TOKEN}` は環境変数から読み込まれます。WinSW設定ファイルで設定した値が使用されます。

---

## サービスの登録と起動

### ステップ1: 管理者権限でコマンドプロンプトを開く

1. スタートメニューで「cmd」を検索
2. 右クリック → 「管理者として実行」

### ステップ2: プロジェクトディレクトリに移動

```cmd
cd /d f:\Project\ToyCITool
```

### ステップ3: サービスのインストール

```cmd
ToyCITool.exe install
```

成功すると以下のようなメッセージが表示されます：
```
Service 'ToyCITool' was installed successfully.
```

### ステップ4: サービスの起動

```cmd
ToyCITool.exe start
```

または、Windowsサービス管理ツールから起動：
```cmd
services.msc
```
→ 「ToyCITool CI Service」を探して右クリック → 「開始」

### ステップ5: サービスの状態確認

```cmd
ToyCITool.exe status
```

または、PowerShellで：
```powershell
Get-Service ToyCITool
```

---

## サービスの管理

### 基本的なコマンド

すべてのコマンドは管理者権限で実行してください。

```cmd
# サービスの起動
ToyCITool.exe start

# サービスの停止
ToyCITool.exe stop

# サービスの再起動
ToyCITool.exe restart

# サービスの状態確認
ToyCITool.exe status

# サービスのアンインストール
ToyCITool.exe uninstall
```

### Windowsサービス管理ツールでの管理

1. `services.msc` を実行
2. 「ToyCITool CI Service」を探す
3. 右クリックでメニューを表示
   - 開始 / 停止 / 再起動
   - プロパティ → スタートアップの種類を変更
   - プロパティ → ログオン → サービスアカウントを変更

### ログの確認

WinSWのログファイルは以下の場所に保存されます：

```
f:\Project\ToyCITool\ToyCITool.out.log  # 標準出力
f:\Project\ToyCITool\ToyCITool.err.log  # エラー出力
f:\Project\ToyCITool\ToyCITool.wrapper.log  # WinSWのログ
```

アプリケーションのログは：
```
f:\Project\ToyCITool\log\
```

ログをリアルタイムで確認するには：
```cmd
# PowerShellで
Get-Content ToyCITool.out.log -Wait -Tail 50
```

---

## トラブルシューティング

### 問題1: サービスが起動しない

**症状**: `ToyCITool.exe start` を実行してもサービスが起動しない

**確認事項**:

1. **ログファイルを確認**
   ```cmd
   type ToyCITool.err.log
   type ToyCITool.wrapper.log
   ```

2. **Pythonのパスが正しいか確認**
   ```cmd
   where python
   ```
   `ToyCITool.xml` の `<executable>` と一致しているか確認

3. **作業ディレクトリが正しいか確認**
   ```cmd
   cd /d f:\Project\ToyCITool
   dir
   ```
   `src` ディレクトリが存在するか確認

4. **依存ライブラリがインストールされているか確認**
   ```cmd
   python -m pip list | findstr "fastapi uvicorn GitPython"
   ```

5. **手動実行でエラーが出ないか確認**
   ```cmd
   cd /d f:\Project\ToyCITool
   python -m src.main
   ```

### 問題2: Git pushが失敗する（認証エラー）

**症状**: ログに認証エラーが記録される

**解決方法**:

1. **アクセストークンが正しく設定されているか確認**
   
   `ToyCITool.xml` を確認：
   ```xml
   <env name="GIT_ACCESS_TOKEN" value="your_actual_token_here"/>
   ```

2. **トークンの権限を確認**
   - GitHub: `repo` 権限が必要
   - GitLab: `api` または `write_repository` 権限が必要
   - Gitea: `write:repository` 権限が必要

3. **トークンの有効期限を確認**
   
   トークンが期限切れになっていないか確認

4. **手動でGit操作をテスト**
   ```cmd
   cd /d f:\Project\ToyCITool\workspace\Example
   git remote -v
   git push origin main
   ```

5. **ログで認証情報が使用されているか確認**
   
   `log\` ディレクトリ内のログファイルで以下を確認：
   ```
   アクセストークンを使用して http://***@localhost:3000/... をクローンしています
   Push前にremote URLを認証付きURLに更新しました
   ```

### 問題3: 環境変数が読み込まれない

**症状**: `config.yaml` の `${GIT_ACCESS_TOKEN}` が展開されない

**解決方法**:

1. **WinSW設定ファイルで環境変数を設定**
   
   `.env` ファイルではなく、`ToyCITool.xml` で設定：
   ```xml
   <env name="GIT_ACCESS_TOKEN" value="your_token"/>
   ```

2. **サービスを再起動**
   ```cmd
   ToyCITool.exe restart
   ```

3. **環境変数の展開を確認**
   
   ログファイルで確認するか、テストスクリプトを実行：
   ```python
   import os
   print(f"GIT_ACCESS_TOKEN: {os.environ.get('GIT_ACCESS_TOKEN', 'NOT SET')}")
   ```

### 問題4: ワークスペースのアクセス権限エラー

**症状**: ファイルの作成や削除ができない

**解決方法**:

1. **サービスアカウントの権限を確認**
   
   デフォルトの `LOCAL SYSTEM` アカウントは通常十分な権限を持っていますが、
   ネットワークドライブやセキュリティ設定によっては問題が発生する場合があります。

2. **専用のサービスアカウントを使用**
   
   `ToyCITool.xml` に追加：
   ```xml
   <serviceaccount>
     <domain>.</domain>  <!-- ローカルアカウントの場合 -->
     <user>ToyCIService</user>
     <password>SecurePassword123!</password>
     <allowservicelogon>true</allowservicelogon>
   </serviceaccount>
   ```

3. **ワークスペースディレクトリの権限を設定**
   ```cmd
   icacls f:\Project\ToyCITool\workspace /grant ToyCIService:(OI)(CI)F
   ```

### 問題5: サービスが予期せず停止する

**症状**: サービスが起動後すぐに停止する

**確認事項**:

1. **エラーログを確認**
   ```cmd
   type ToyCITool.err.log
   ```

2. **Pythonスクリプトのエラーを確認**
   ```cmd
   type log\app.log
   ```

3. **ポートが既に使用されていないか確認**
   ```cmd
   netstat -ano | findstr :8000
   ```

4. **再起動設定を確認**
   
   `ToyCITool.xml` の `<onfailure>` 設定を確認

---

## セキュリティに関する注意事項

### 1. アクセストークンの管理

**重要**: `ToyCITool.xml` にはGitアクセストークンが平文で記載されます。

**推奨される対策**:

1. **ファイルのアクセス権限を制限**
   ```cmd
   icacls ToyCITool.xml /inheritance:r
   icacls ToyCITool.xml /grant:r "%USERNAME%:(R,W)"
   icacls ToyCITool.xml /grant:r "Administrators:(F)"
   ```

2. **トークンの権限を最小限に**
   - 必要なリポジトリのみにアクセス可能なトークンを使用
   - 読み取り専用が可能な場合は読み取り専用トークンを使用

3. **トークンの定期的な更新**
   - 有効期限を設定し、定期的に更新

4. **バージョン管理から除外**
   - `.gitignore` に `ToyCITool.xml` を追加（トークンを記載した後）
   ```
   # .gitignore
   ToyCITool.xml
   ToyCITool.exe
   *.log
   ```

### 2. サービスアカウントの設定

**推奨**: `LOCAL SYSTEM` アカウントではなく、専用のサービスアカウントを使用

**手順**:

1. **専用ユーザーアカウントを作成**
   ```cmd
   net user ToyCIService SecurePassword123! /add
   net localgroup Users ToyCIService /delete
   ```

2. **必要最小限の権限を付与**
   - ToyCIToolディレクトリへの読み取り/書き込み権限
   - Gitへのアクセス権限
   - ネットワークアクセス権限（必要な場合）

3. **サービスログオン権限を付与**
   - ローカルセキュリティポリシー → ユーザー権利の割り当て
   - 「サービスとしてログオン」に追加

4. **ToyCITool.xmlで設定**
   ```xml
   <serviceaccount>
     <domain>.</domain>
     <user>ToyCIService</user>
     <password>SecurePassword123!</password>
     <allowservicelogon>true</allowservicelogon>
   </serviceaccount>
   ```

### 3. ネットワークセキュリティ

1. **ファイアウォール設定**
   - 必要なポート（デフォルト: 8000）のみを開放
   - 信頼できるIPアドレスからのアクセスのみを許可

2. **HTTPS通信**
   - 可能な限りHTTPSを使用
   - リバースプロキシ（nginx, IISなど）の使用を検討

### 4. ログのセキュリティ

1. **ログファイルのアクセス制限**
   ```cmd
   icacls log /inheritance:r
   icacls log /grant:r "Administrators:(OI)(CI)F"
   icacls log /grant:r "ToyCIService:(OI)(CI)RW"
   ```

2. **機密情報のマスキング**
   - アクセストークンは自動的にマスクされます（`*****`）
   - ログに機密情報が含まれていないか定期的に確認

---

## 参考リンク

- [WinSW公式ドキュメント](https://github.com/winsw/winsw/blob/v3/docs/index.md)
- [Windowsサービスの管理](https://docs.microsoft.com/ja-jp/windows-server/administration/windows-commands/sc-config)
- [Git認証情報の管理](https://git-scm.com/book/ja/v2/Git-%E3%81%AE%E3%81%95%E3%81%BE%E3%81%96%E3%81%BE%E3%81%AA%E3%83%84%E3%83%BC%E3%83%AB-%E8%AA%8D%E8%A8%BC%E6%83%85%E5%A0%B1%E3%81%AE%E4%BF%9D%E5%AD%98)

---

## まとめ

このガイドに従うことで、ToyCIToolをWindowsサービスとして安全かつ確実に実行できます。

**重要なポイント**:
1. ✅ WinSW設定ファイルで環境変数を明示的に設定
2. ✅ 絶対パスを使用
3. ✅ アクセストークンのセキュリティに注意
4. ✅ ログファイルで動作を確認
5. ✅ 定期的なメンテナンスとトークンの更新

問題が発生した場合は、まずログファイルを確認し、このドキュメントのトラブルシューティングセクションを参照してください。
