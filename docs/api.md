# API ドキュメント

ToyCI Serverが提供するREST APIのエンドポイント仕様です。

## アーキテクチャ

APIは FastAPI フレームワークを使用して実装されており、以下の特徴があります：

*   **Lifespan イベント**: アプリケーション起動時に DIコンテナを初期化し、設定を読み込みます。
*   **Dependency Injection**: [`Container`](../src/core/container.py:1) を通じてサービスインスタンスを取得します。
*   **非同期処理**: Webhookイベントの処理は `BackgroundTasks` を使用してバックグラウンドで実行されます。

## エンドポイント

### POST `/webhook`

VCSプロバイダー（主にGitHub）からのWebhookイベントを受け取ります。

*   **URL**: `/webhook`
*   **Method**: `POST`
*   **Content-Type**: `application/json`

#### ヘッダー

| ヘッダー名 | 説明 |
| --- | --- |
| `X-GitHub-Event` | GitHubイベントの種類（例: `push`）。プロバイダー判定に使用されます。 |
| その他 | プロバイダー固有のヘッダーが含まれる場合があります。 |

**注意**: ヘッダー名の大文字小文字は区別されません（FastAPIが正規化します）。

#### リクエストボディ

VCSプロバイダーから送信されるJSONペイロード。
GitHubの場合、`commits` 配列や `head_commit` 情報が含まれます。

**例 (GitHub Push Event - 一部抜粋):**

```json
{
  "ref": "refs/heads/main",
  "commits": [
    {
      "id": "c4413f5e8b2a1d3c7f9e0a6b8d4e2f1a3c5b7d9e",
      "message": "Update README.md",
      "timestamp": "2024-01-01T00:00:00+09:00",
      "added": [],
      "removed": [],
      "modified": ["README.md"]
    }
  ],
  "head_commit": {
    "id": "c4413f5e8b2a1d3c7f9e0a6b8d4e2f1a3c5b7d9e",
    "message": "Update README.md",
    "modified": ["README.md"]
  }
}
```

#### 処理フロー

1.  **ペイロード解析**: JSONペイロードをパースします。
2.  **プロバイダー判定**: [`WebhookProviderFactory`](../src/core/webhook_factory.py:1) がヘッダーに基づいてプロバイダーを選択します。
3.  **スキップ判定**: プロバイダーの `should_skip()` メソッドでスキップ判定を行います（例: `[ci skip]` の検出）。
4.  **変更ファイル抽出**: プロバイダーの `extract_changed_files()` メソッドで変更ファイルを抽出します。
5.  **ジョブマッチング**: [`JobMatcher`](../src/core/job_matcher.py:1) が各ジョブの `watch_files` パターンと照合します。
6.  **バックグラウンド実行**: マッチしたジョブを `BackgroundTasks` に追加し、非同期で実行します。
7.  **レスポンス返却**: トリガーされたジョブ名のリストを即座に返します（ジョブの完了を待ちません）。

#### レスポンス

*   **Status Code**: `200 OK`
*   **Content-Type**: `application/json`

**成功時:**

```json
{
  "status": "ok",
  "triggered_jobs": ["job_name_1", "job_name_2"]
}
```

*   `status`: 処理状態 ("ok" または "error")
*   `triggered_jobs`: トリガーされたジョブ名のリスト（空リストの場合もあります）

**エラー時 (JSONパースエラー等):**

```json
{
  "status": "error",
  "message": "Invalid JSON payload"
}
```

**エラー時 (内部エラー):**

```json
{
  "status": "error",
  "message": "Internal Server Error"
}
```

## エラーハンドリング

### JSONパースエラー

無効なJSONペイロードの場合、エラーログを出力し、ステータス `error` とメッセージを返します。

```python
try:
    payload = await request.json()
except Exception as e:
    logger.error(f"JSONペイロードの解析エラー: {e}")
    return {"status": "error", "message": "Invalid JSON payload"}
```

### プロバイダー判定

対応していないプロバイダーの場合、デフォルトでGitHubとして処理を試みます。ペイロード構造が異なると正しく動作しない可能性があります。

```python
provider = WebhookProviderFactory.get_provider(dict(request.headers))
logger.info(f"プロバイダーを使用: {provider.get_provider_id()}")
```

### 内部処理エラー

ジョブトリガーサービスでの例外は捕捉され、ログに記録されます。APIレスポンスとしては `200 OK` または `error` ステータスを返します。

```python
try:
    triggered_jobs = service.process_webhook_event(provider, payload, background_tasks)
    return {"status": "ok", "triggered_jobs": triggered_jobs}
except Exception as e:
    logger.exception(f"Webhook processing failed: {e}")
    return {"status": "error", "message": "Internal Server Error"}
```

### バックグラウンドタスクのエラー

バックグラウンドで実行されるジョブのエラーは、ログに記録されますが、APIレスポンスには影響しません（既にレスポンスが返された後のため）。

## 実装詳細

### Lifespan イベント

アプリケーションの起動時と終了時に実行される処理です。

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 起動時
    setup_logging()
    container = get_container()
    app.state.container = container
    logger.info("Application started with configuration loaded.")
    
    yield
    
    # 終了時
    logger.info("Application shutdown.")
```

### DIコンテナの使用

各リクエストで、`app.state.container` からサービスインスタンスを取得します。

```python
container = request.app.state.container
service = container.job_trigger_service
```

これにより、以下の利点があります：

*   **シングルトン管理**: 設定やサービスインスタンスが一度だけ初期化されます。
*   **テスタビリティ**: モックやスタブに置き換えやすくなります。
*   **依存関係の明確化**: サービス間の依存関係が明示的になります。

### バックグラウンドタスク

ジョブの実行は `BackgroundTasks` を使用して非同期で行われます。

```python
background_tasks.add_task(self.job_service.run_job, job_dict, payload_meta)
```

これにより、Webhookリクエストに対して即座にレスポンスを返すことができます。

## セキュリティ考慮事項

### アクセストークンの保護

*   アクセストークンは環境変数または `.env` ファイルで管理してください。
*   ログ出力時は [`mask_auth_token()`](../src/core/vcs_utils.py:32) でマスクされます。
*   設定ファイルに直接記述しないでください。

### Webhook署名検証

**現在未実装**: GitHubのWebhook署名検証（`X-Hub-Signature-256`）は実装されていません。本番環境では実装を推奨します。

### 無限ループ防止

CIツールが生成したコミットには自動的に `[skip ci]` が付与され、再度Webhookがトリガーされても処理がスキップされます。

```python
def should_skip(self, payload: Dict[str, Any]) -> bool:
    message = payload.get("head_commit", {}).get("message", "").lower()
    return "ci skip" in message or "[ci skip]" in message
```

## 使用例

### curlでのテスト

```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: push" \
  -d '{
    "commits": [
      {
        "id": "abc123",
        "message": "Update code",
        "added": [],
        "modified": ["src/main.py"],
        "removed": []
      }
    ],
    "head_commit": {
      "id": "abc123",
      "message": "Update code"
    }
  }'
```

### GitHubでのWebhook設定

1.  リポジトリの **Settings** → **Webhooks** → **Add webhook** を選択
2.  **Payload URL**: `http://your-server:8000/webhook`
3.  **Content type**: `application/json`
4.  **Which events would you like to trigger this webhook?**: `Just the push event`
5.  **Active**: チェックを入れる
6.  **Add webhook** をクリック

### ログの確認

ジョブの実行状況は、設定されたログファイル（デフォルト: `log/toyci.log`）で確認できます。

```bash
# Windowsの場合
type log\toyci.log

# Linux/Macの場合
tail -f log/toyci.log
```

## トラブルシューティング

### Webhookが受信されない

*   サーバーが起動しているか確認してください。
*   ファイアウォールやネットワーク設定を確認してください。
*   GitHubのWebhook設定で「Recent Deliveries」を確認してください。

### ジョブがトリガーされない

*   `triggered_jobs` が空リストで返されていないか確認してください。
*   ログで「スキップされました」というメッセージを確認してください。
*   `watch_files` のパターンが変更ファイルにマッチしているか確認してください。

### JSONパースエラー

*   Content-Type が `application/json` になっているか確認してください。
*   ペイロードが有効なJSON形式か確認してください。

### 内部サーバーエラー

*   ログファイルで詳細なエラーメッセージを確認してください。
*   設定ファイル（`config.yaml`）が正しいか確認してください。
*   必要な環境変数が設定されているか確認してください。
