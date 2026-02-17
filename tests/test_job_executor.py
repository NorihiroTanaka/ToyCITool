"""ShellJobExecutorのテスト。"""

from unittest.mock import patch, MagicMock
import subprocess

import pytest

from src.core.job_executor import ShellJobExecutor
from src.core.exceptions import ScriptExecutionError


class TestShellJobExecutor:
    """ShellJobExecutorのテスト。"""

    def setup_method(self):
        self.executor = ShellJobExecutor()

    @patch("src.core.job_executor.subprocess.run")
    def test_スクリプト成功時に例外が発生しない(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        # 例外が発生しないこと
        self.executor.execute("echo hello", "/tmp")
        mock_run.assert_called_once_with(
            "echo hello", shell=True, cwd="/tmp", capture_output=True, text=True
        )

    @patch("src.core.job_executor.subprocess.run")
    def test_スクリプト失敗時にScriptExecutionErrorが発生する(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="some output",
            stderr="some error",
        )
        with pytest.raises(ScriptExecutionError) as exc_info:
            self.executor.execute("exit 1", "/tmp")

        assert exc_info.value.stdout == "some output"
        assert exc_info.value.stderr == "some error"
        assert exc_info.value.return_code == 1

    @patch("src.core.job_executor.subprocess.run")
    def test_ScriptExecutionErrorのメッセージにstdout_stderrが含まれる(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=2,
            stdout="output text",
            stderr="error text",
        )
        with pytest.raises(ScriptExecutionError) as exc_info:
            self.executor.execute("bad_script", "/tmp")

        message = str(exc_info.value)
        assert "output text" in message
        assert "error text" in message
