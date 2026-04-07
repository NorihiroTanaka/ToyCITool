import subprocess
import logging
import os
import sys
import threading
from datetime import datetime
from typing import Optional, Dict

from .interfaces import IJobExecutor
from .exceptions import ScriptExecutionError, JobTimeoutError

logger = logging.getLogger(__name__)

_DEFAULT_JOB_LOG_DIR = "log/jobs"


class ShellJobExecutor(IJobExecutor):
    def __init__(self, job_log_dir: str = _DEFAULT_JOB_LOG_DIR):
        self.job_log_dir = os.path.abspath(job_log_dir)

    def _create_log_file_path(self, job_name: str) -> str:
        """ジョブ名とタイムスタンプからログファイルパスを生成する"""
        os.makedirs(self.job_log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{job_name}_{timestamp}.log"
        return os.path.join(self.job_log_dir, filename)

    def _build_env(self, env: Optional[Dict[str, str]] = None, venv: Optional[str] = None) -> Dict[str, str]:
        """ホスト環境変数をベースに、venvおよび追加の環境変数をマージした辞書を返す"""
        merged = os.environ.copy()
        if venv:
            venv_abs = os.path.abspath(venv)
            scripts_dir = os.path.join(venv_abs, "Scripts" if sys.platform == "win32" else "bin")
            current_path = merged.get("PATH", "")
            merged["PATH"] = scripts_dir + os.pathsep + current_path
            merged["VIRTUAL_ENV"] = venv_abs
            merged.pop("PYTHONHOME", None)
        if env:
            merged.update(env)
        return merged

    def _terminate_process(self, process: subprocess.Popen, job_name: str) -> None:
        """プロセスを段階的に終了する（terminate → 待機 → kill）"""
        if process.poll() is not None:
            return

        logger.warning(f"[{job_name}] プロセスを終了中...")
        try:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(f"[{job_name}] terminate後もプロセスが生存。killで強制終了します。")
                process.kill()
                process.wait()
        except OSError:
            pass

    def execute(self, script: str, cwd: str, job_name: str = "unknown", env: Optional[Dict[str, str]] = None, timeout_seconds: Optional[int] = None, venv: Optional[str] = None) -> None:
        """シェルスクリプトをリアルタイムログ出力付きで実行する"""
        log_file_path = self._create_log_file_path(job_name)
        logger.info(f"[{job_name}] スクリプトを実行中: {script}")
        logger.info(f"[{job_name}] ジョブログ: {log_file_path}")
        if venv is not None:
            logger.info(f"[{job_name}] Python venv: {os.path.abspath(venv)}")
        if timeout_seconds is not None:
            logger.info(f"[{job_name}] タイムアウト: {timeout_seconds}秒")

        process_env = self._build_env(env, venv)
        output_lines: list[str] = []
        timed_out = threading.Event()
        timer: Optional[threading.Timer] = None

        try:
            with open(log_file_path, "w", encoding="utf-8") as log_file:
                process = subprocess.Popen(
                    script,
                    shell=True,
                    cwd=cwd,
                    env=process_env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )

                if timeout_seconds is not None:
                    def _on_timeout():
                        timed_out.set()
                        timeout_msg = f"[{job_name}] タイムアウトにより強制終了 ({timeout_seconds}秒)\n"
                        log_file.write(timeout_msg)
                        log_file.flush()
                        logger.error(f"[{job_name}] タイムアウトにより強制終了 ({timeout_seconds}秒)")
                        self._terminate_process(process, job_name)

                    timer = threading.Timer(timeout_seconds, _on_timeout)
                    timer.daemon = True
                    timer.start()

                try:
                    for line in process.stdout:
                        log_file.write(line)
                        log_file.flush()
                        logger.info(f"[{job_name}] {line.rstrip()}")
                        output_lines.append(line)

                    process.wait()
                finally:
                    if timer is not None:
                        timer.cancel()
                    if process.poll() is None:
                        process.kill()
                        process.wait()

        except OSError as e:
            error_msg = f"[{job_name}] スクリプトの起動に失敗しました: {e}"
            logger.error(error_msg)
            raise ScriptExecutionError(
                error_msg,
                stdout="".join(output_lines),
                stderr="",
                return_code=-1,
            )

        if timed_out.is_set():
            full_output = "".join(output_lines)
            error_msg = (
                f"[{job_name}] タイムアウトにより強制終了されました "
                f"({timeout_seconds}秒)"
            )
            raise JobTimeoutError(
                error_msg,
                stdout=full_output,
                stderr="",
                return_code=-1,
                timeout_seconds=timeout_seconds,
            )

        return_code = process.returncode
        full_output = "".join(output_lines)

        if return_code != 0:
            error_msg = (
                f"[{job_name}] スクリプトが失敗しました (終了コード: {return_code}):\n"
                f"STDOUT: {full_output}"
            )
            logger.error(f"[{job_name}] スクリプトが終了コード {return_code} で失敗しました。")
            raise ScriptExecutionError(
                error_msg,
                stdout=full_output,
                stderr="",
                return_code=return_code,
            )

        logger.info(f"[{job_name}] スクリプトが正常に終了しました。")
