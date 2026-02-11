import subprocess
import logging
import os
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

from .interfaces import IJobExecutor

class ShellJobExecutor(IJobExecutor):
    def execute(self, script: str, cwd: str) -> None:
        """シェルスクリプトを実行する"""
        logger.info(f"スクリプトを実行中: {script}")
        # スクリプト実行 (shell=Trueで実行)
        result = subprocess.run(script, shell=True, cwd=cwd, capture_output=True, text=True)
        
        if result.returncode != 0:
            error_msg = f"スクリプトが失敗しました:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        logger.info(f"スクリプトが正常に終了しました。")
