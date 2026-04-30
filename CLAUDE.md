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

プロジェクト構成・アーキテクチャの確認は `.agents/skills/project-structure/SKILL.md` のスキルを使用すること。

## 開発規約

### 言語
- コミュニケーション・コメント・Docstringはすべて **日本語**

### プログラミングスタイル
- **関数型プログラミング**: 純粋関数を優先、副作用をシステム境界に分離
- **不変性**: `NamedTuple`、`frozen dataclass`、Pydanticモデルを活用
- **型ヒント**: すべての関数に引数・戻り値の型を記述
- **宣言的記述**: リスト内包表記、`map`/`filter`、高階関数を活用

### 開発フロー（TDD）

「TDDで実装して」「テスト駆動で作って」「テストファーストで開発して」などTDDを求める指示があった場合は、`.agents/skills/tdd-workflow/SKILL.md` のワークフローに従って開発すること。

タスクの粒度が大きい（複数ステップが必要、複数ファイルにまたがるなど）と判断した場合は、`.agents/skills/task-splitter/SKILL.md` の使用を検討すること。

### テスト規約

tdd-workflow スキル経由でテストを書く場合も含め、以下の規約に準拠すること:
- AAA（Arrange-Act-Assert）パターン厳守
- テスト間の独立性を保つ（共有状態禁止）
- 外部依存はモックで分離

### リファクタリング

リファクタリング・設計改善・コード整理を行う場合は、`.agents/skills/refactor-planner/SKILL.md` のスキルを使用すること。

### バグ修正・エラー修正

バグ修正・エラー修正・問題修正を行う場合は、`.agents/skills/fix-with-plan/SKILL.md` のスキルを使用すること。
計画なしに即実装しないこと。

## スキル活用ガイド

| 状況 | 使用するスキル |
|------|---------------|
| プロジェクト構成・アーキテクチャを確認したい | `.agents/skills/project-structure/SKILL.md` |
| タスクをサブタスクに分割したい（粒度が大きい場合） | `.agents/skills/task-splitter/SKILL.md` |
| TDD（テスト駆動開発）で実装したい | `.agents/skills/tdd-workflow/SKILL.md` |
| リファクタリング・設計改善・コード整理をしたい | `.agents/skills/refactor-planner/SKILL.md` |
| バグ修正・エラー修正・問題修正をしたい | `.agents/skills/fix-with-plan/SKILL.md` |

## 設計パターン
- **DI（依存性注入）**: `Container`クラスでサービスインスタンス管理
- **Factory**: `WebhookProviderFactory`でプロバイダ選択
- **Strategy**: `IJobMatcher`インターフェースで柔軟なマッチング

## コアコンセプト
- **Docker非依存**: ホストOS上で直接動作、外部ミドルウェア不要
- **容易な設定**: 最小限の設定で動作するデフォルト値を提供
