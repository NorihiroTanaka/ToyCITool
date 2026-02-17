import subprocess
import logging
import os
from datetime import datetime

from .interfaces import IJobExecutor
from .exceptions import ScriptExecutionError

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

    def execute(self, script: str, cwd: str, job_name: str = "unknown") -> None:
        """シェルスクリプトをリアルタイムログ出力付きで実行する"""
        log_file_path = self._create_log_file_path(job_name)
        logger.info(f"[{job_name}] スクリプトを実行中: {script}")
        logger.info(f"[{job_name}] ジョブログ: {log_file_path}")

        output_lines: list[str] = []

        try:
            with open(log_file_path, "w", encoding="utf-8") as log_file:
                process = subprocess.Popen(
                    script,
                    shell=True,
                    cwd=cwd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )

                try:
                    for line in process.stdout:
                        log_file.write(line)
                        log_file.flush()
                        logger.info(f"[{job_name}] {line.rstrip()}")
                        output_lines.append(line)

                    process.wait()
                finally:
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
