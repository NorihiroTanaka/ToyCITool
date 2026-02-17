import subprocess
import logging

from .interfaces import IJobExecutor
from .exceptions import ScriptExecutionError

logger = logging.getLogger(__name__)


class ShellJobExecutor(IJobExecutor):
    def execute(self, script: str, cwd: str) -> None:
        """シェルスクリプトを実行する"""
        logger.info(f"スクリプトを実行中: {script}")
        result = subprocess.run(script, shell=True, cwd=cwd, capture_output=True, text=True)

        if result.returncode != 0:
            error_msg = f"スクリプトが失敗しました:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
            logger.error(error_msg)
            raise ScriptExecutionError(
                error_msg,
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode,
            )

        logger.info(f"スクリプトが正常に終了しました。")
