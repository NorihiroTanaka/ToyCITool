# CLAUDE.md

## プロジェクト概要

ToyCIToolは軽量なオンプレミスCIサーバー。Gitサーバー（GitHub/GitLab/Gitea等）からWebhookを受信し、指定ファイルの変更を検知してシェルスクリプトを自動実行する。

## 技術スタック

- **言語**: Python 3.x
- **フレームワーク**: FastAPI + Uvicorn (ASGI)
- **主要ライブラリ**: GitPython, PyYAML, Pydantic, python-dotenv
- **テスト**: pytest
- **デプロイ**: WinSW (Windowsサービス)

## コマンド

```bash
# 開発サーバー起動（ホットリロード付き）
python -m src.main
python -m src.main --port 8080

# テスト実行
pytest
pytest tests/test_job_matcher.py -v
pytest -k "test_match"

# デフォルト設定の表示
python -m src.main --print-default-config
```

## プロジェクト構成

```
src/
  main.py              # エントリーポイント（CLI）
  api.py               # FastAPIアプリ（/webhook エンドポイント）
  core/
    config.py           # Pydantic設定モデル（環境変数展開対応）
    container.py        # DIコンテナ（シングルトン）
    interfaces.py       # 抽象基底クラス（ABC）
    job_service.py      # ジョブ実行オーケストレーション
    job_trigger.py      # Webhookイベント処理
    job_matcher.py      # ファイルパターンマッチング
    webhook_handler.py  # WebhookProvider実装
    webhook_factory.py  # プロバイダファクトリ
    vcs_handler.py      # Git操作（GitPythonラッパー）
    job_executor.py     # シェルスクリプト実行
    workspace_manager.py # ワークスペース管理
    notifier.py         # 通知（Discord対応）
    repo_ci_config_loader.py # リポジトリ内.toyci.yaml読込
    exceptions.py       # カスタム例外
tests/                  # pytestテストスイート
config.yaml             # ジョブ設定
```

## 開発規約

### 言語
- コミュニケーション・コメント・Docstringはすべて **日本語**

### プログラミングスタイル
- **関数型プログラミング**: 純粋関数を優先、副作用をシステム境界に分離
- **不変性**: `NamedTuple`、`frozen dataclass`、Pydanticモデルを活用
- **型ヒント**: すべての関数に引数・戻り値の型を記述
- **宣言的記述**: リスト内包表記、`map`/`filter`、高階関数を活用

### 開発フロー（TDD）
1. **シグネチャ設計**: 関数名・型・Docstringを先に定義（`pass`で仮実装）
2. **テスト実装**: 正常系・異常系・境界値のテストを先に書く（Red）
3. **実装**: テストを通す最小限のコードを書く（Green → Refactor）

### テスト規約
- AAA（Arrange-Act-Assert）パターン厳守
- テスト間の独立性を保つ（共有状態禁止）
- 外部依存はモックで分離

### リファクタリング
- 振る舞いを保存する（機能追加・バグ修正と同時に行わない）
- テストがグリーンの状態から開始し、小さな変更を繰り返す
- 単一責任原則・低結合・高凝集を目指す

## 設計パターン
- **DI（依存性注入）**: `Container`クラスでサービスインスタンス管理
- **Factory**: `WebhookProviderFactory`でプロバイダ選択
- **Strategy**: `IJobMatcher`インターフェースで柔軟なマッチング

## コアコンセプト
- **Docker非依存**: ホストOS上で直接動作、外部ミドルウェア不要
- **容易な設定**: 最小限の設定で動作するデフォルト値を提供
