# TASK-001: リアルタイムログ出力の実装

## 1. タスク概要
ジョブ実行時のログ出力を、現在の「終了後にまとめて出力・保存」する方式から、「実行中にリアルタイムでファイルに出力し、かつコンソールにもストリーミングする」方式へ変更する。

## 2. 現状の課題
*   **現状:** `subprocess.run` 等でコマンドを実行し、完了後に `stdout` / `stderr` を取得しているため、長時間実行されるジョブ（ビルドやテストなど）の進捗が途中で確認できない。
*   **問題点:** ジョブがハングアップしているのか、単に処理に時間がかかっているのか判別できない。デバッグが困難。

## 3. 仕様・要件

### コアコンセプトへの適合
*   **Docker非依存 (No Docker Dependency):**
    *   ログ収集は、Dockerコンテナのログドライバ等に依存せず、ホストOS上で実行されるサブプロセスの標準出力/標準エラー出力を直接パイプでキャプチャすることで実現する。
    *   これにより、実行環境にDockerがインストールされていなくても機能することを保証する。
*   **容易な設定 (Easy Configuration):**
    *   ユーザーによる追加設定は不要（Zero Config）。
    *   ログの保存場所やフォーマットは適切なデフォルト値（例: `logs/jobs/` 配下）を提供し、意識せずに利用可能にする。

### 実装内容
*   **対象ファイル:** `src/core/job_executor.py` (主に `JobExecutor` クラス)
*   **使用技術:**
    *   Python `subprocess.Popen` を使用し、`stdout` と `stderr` をパイプ (`subprocess.PIPE`) で接続する。
    *   別スレッドまたは非同期I/Oを用いて、パイプからの出力を逐次読み取る。
    *   Python `logging` モジュールとの連携、またはファイルへの直接書き込み。

### 期待される挙動
1.  ジョブ開始時にログファイルを作成する（例: `logs/jobs/{job_id}.log`）。
2.  サブプロセスの標準出力・標準エラー出力を1行ずつ読み取る。
3.  読み取った行を即座に:
    *   ログファイルに追記する。
    *   アプリケーションのコンソール（標準出力）にも表示する（オプション）。
4.  プロセス終了までこれを継続する。

### コード変更イメージ (概念)
```python
# 変更前 (イメージ)
result = subprocess.run(cmd, capture_output=True, text=True)
save_log(result.stdout)

# 変更後 (イメージ)
with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1) as proc:
    for line in proc.stdout:
        print(line, end='') # コンソール出力
        log_file.write(line) # ファイル出力
```

## 4. 優先度
**High**
（CIツールとして、実行状況の可視化は最も基本的な機能要件の一つであるため）
