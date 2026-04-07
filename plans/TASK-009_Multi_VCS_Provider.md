# TASK-009: 複数VCSプロバイダー対応（GitLab / Gitea / Bitbucket）

## 1. タスク概要
現在GitHub形式のみに対応しているWebhookペイロード解析を、GitLab・Gitea・Bitbucketにも対応させる。既存の `WebhookProviderFactory` パターンを活用して拡張する。

## 2. 現状の課題
*   **現状:** `webhook_factory.py` にFactoryパターンが実装されているが、実際にはGitHub形式のみ対応。
*   **問題点:** Giteaなどのセルフホスト型Gitサーバーからのイベントを正しく処理できない。ペイロード形式の差異（フィールド名、ネスト構造）を吸収する仕組みが必要。

## 3. 仕様・要件

### コアコンセプトへの適合
*   **Docker非依存:** 外部依存なし。ペイロードのJSON解析ロジックのみ。
*   **容易な設定:** ヘッダーからプロバイダーを自動判別するため、設定不要で動作させる。

### 実装内容
*   **対象ファイル:**
    *   `src/core/webhook_factory.py`: プロバイダー判別ロジックの拡張。
    *   `src/core/providers/` (新規ディレクトリ): 各プロバイダーの実装。
        *   `github.py`: 既存ロジックの移設。
        *   `gitlab.py`: GitLab webhook対応。
        *   `gitea.py`: Gitea webhook対応。
        *   `bitbucket.py`: Bitbucket webhook対応。

### プロバイダー自動判別ルール
| ヘッダー | プロバイダー |
|---|---|
| `X-GitHub-Event` | GitHub |
| `X-Gitlab-Event` | GitLab |
| `X-Gitea-Event` | Gitea |
| `X-Event-Key` | Bitbucket |

### 期待される挙動
1.  受信したWebhookのヘッダーからプロバイダーを自動判別する。
2.  各プロバイダー固有のペイロード形式から、共通のデータモデル（リポジトリURL、ブランチ、変更ファイル一覧、コミット情報）に正規化する。
3.  正規化後のデータは既存のジョブマッチング・実行パイプラインにそのまま流す。
4.  不明なプロバイダーの場合はGitHub互換として処理を試み、パース失敗時はエラーレスポンスを返す。

## 4. 優先度
**Medium**
（セルフホスト環境（Gitea等）で利用する場合は必須。Factoryパターンが整備済みのため実装コストは低い）
