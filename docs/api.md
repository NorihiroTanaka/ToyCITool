# API ドキュメント

ToyCI Serverが提供するREST APIのエンドポイント仕様です。

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

#### リクエストボディ

VCSプロバイダーから送信されるJSONペイロード。
GitHubの場合、`commits` 配列や `head_commit` 情報が含まれます。

**例 (GitHub Push Event - 一部抜粋):**

```json
{
  "ref": "refs/heads/main",
  "commits": [
    {
      "id": "c4413...",
      "message": "Update README.md",
      "timestamp": "2024-01-01T00:00:00+09:00",
      "added": [],
      "removed": [],
      "modified": ["README.md"]
    }
  ],
  "head_commit": {
    "id": "c4413...",
    "message": "Update README.md",
    "modified": ["README.md"]
  }
}
```

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
*   `triggered_jobs`: トリガーされたジョブ名のリスト

**エラー時 (JSONパースエラー等):**

```json
{
  "status": "error",
  "message": "Invalid JSON payload"
}
```

## エラーハンドリング

*   無効なJSONペイロードの場合、エラーログを出力し、ステータス `error` を返します。
*   対応していないプロバイダーの場合、デフォルトでGitHubとして処理を試みますが、ペイロード構造が異なると正しく動作しない可能性があります。
*   内部処理（ジョブ実行など）での例外はログに記録されますが、APIレスポンスとしては `200 OK` を返し、バックグラウンドタスクとして処理される場合があります（実装依存）。現在は `JobTriggerService` 内で同期的に実行されています。
