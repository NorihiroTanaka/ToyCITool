---
name: project-structure
description: >
  ToyCIToolプロジェクトの構成・アーキテクチャを体系的に確認するスキル。
  「プロジェクトの構成を教えて」「どこに何がある？」「このプロジェクトの概要は？」
  「アーキテクチャを理解したい」「どのファイルを変更すればいい？」といった質問や、
  新機能の実装・リファクタリング・バグ修正を始める前にコンテキストを把握したいときに使う。
  プロジェクト全体の見取り図を素早く提示し、「どこに何があるか」を明確にする。
  ユーザーが特定のモジュールや設定ファイルの場所・役割を尋ねたときも積極的に使う。
---

# Project Structure Checker

ToyCIToolプロジェクトの構成を体系的に確認し、ユーザーに正確なコンテキストを提供する。

## 実行手順

### Step 1: ディレクトリ構造の把握

まずトップレベルのファイル・ディレクトリを把握する:

```
プロジェクトルート/
├── src/              ソースコード
│   ├── api.py        FastAPI エントリーポイント
│   ├── main.py       CLIエントリーポイント
│   └── core/         コアロジック（各モジュール）
├── tests/            テストコード
├── docs/             ドキュメント（overview.md, core_modules.md等）
├── config.yaml       ジョブ・サーバー設定
├── logging.yaml      ログ設定
├── requirements.txt  依存ライブラリ
└── workspace/        ジョブ実行用一時領域（自動生成）
```

### Step 2: ユーザーの質問に応じた詳細確認

ユーザーの質問内容によって読むファイルを絞る:

| ユーザーの関心 | 読むべきファイル |
|---|---|
| 全体像・アーキテクチャ | `docs/overview.md` |
| 各モジュールの役割 | `docs/core_modules.md` |
| 設定の仕方 | `config.yaml`, `docs/configuration.md` |
| 特定モジュールの詳細 | 該当する `src/core/*.py` |
| テスト構成 | `tests/` 配下のファイル一覧 |
| 依存ライブラリ | `requirements.txt` |

**原則**: 最初から全ファイルを読もうとしない。ユーザーが知りたいことを先に特定し、必要なものだけ読む。

### Step 3: 構成情報の提示

以下の観点を含めてわかりやすく伝える:

1. **レイヤー構造** — どのモジュールがどの役割を担うか（API層・ロジック層・インフラ層）
2. **データフロー** — Webhook受信 → ジョブ判定 → スクリプト実行 → Push という処理の流れ
3. **主要な設計パターン** — DI（Container）、Factory（WebhookFactory）、Strategy（JobMatcher）
4. **変更時の影響範囲** — 「この機能を変えるなら、このファイルを見ればよい」という案内

### Step 4: 次のアクションへの橋渡し

構成確認は目的ではなく手段。確認後は:
- 「この部分を修正したい」ならtask-splitterスキルと連携してサブタスクに分解
- 「このモジュールを理解したい」なら該当ファイルを読んで説明
- 「新機能を追加したい」なら影響するファイルを特定して実装に入る

## アーキテクチャのクイックリファレンス

ToyCIToolは **5つのレイヤー** で構成される:

```
[GitHub/GitLab] → WebHook POST
        ↓
[API Layer]          src/api.py
  FastAPI。Webhook受信、DI初期化
        ↓
[Logic Layer]        src/core/job_trigger.py, webhook_handler.py, job_matcher.py
  Webhook解析、変更ファイル抽出、ジョブの実行可否判定
        ↓
[Service Layer]      src/core/job_service.py
  ジョブ実行ライフサイクル管理（準備→実行→後処理）
        ↓
[Infrastructure]     src/core/vcs_handler.py, job_executor.py, workspace_manager.py
  Git操作、スクリプト実行、ファイルシステム管理
```

**設定管理**: `src/core/config.py` (Pydantic) + `config.yaml`  
**DI管理**: `src/core/container.py` (シングルトンコンテナ)  
**インターフェース**: `src/core/interfaces.py` (抽象基底クラス群)

## 注意点

- `workspace/` ディレクトリはジョブ実行時に自動生成される一時領域。コードではない
- `.env` ファイルはGit管理外。`GIT_ACCESS_TOKEN` 等の機密情報を含む
- `config.yaml` 内の `${VAR}` は環境変数展開される
- Windowsサービス実行時は `.env` ではなく `ToyCITool.xml` で環境変数を設定する
