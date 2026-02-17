"""ShellJobExecutorのテスト。"""

import subprocess
from unittest.mock import patch, MagicMock, mock_open

import pytest

from src.core.job_executor import ShellJobExecutor
from src.core.exceptions import ScriptExecutionError


class TestShellJobExecutor:
    """ShellJobExecutorのテスト。"""

    def setup_method(self):
        self.executor = ShellJobExecutor(job_log_dir="/tmp/test_log_jobs")

    def _make_mock_process(self, stdout_lines, returncode):
        """Popenモックプロセスを生成するヘルパー"""
        mock_process = MagicMock()
        mock_process.stdout = iter(stdout_lines)
        mock_process.wait.return_value = returncode
        mock_process.returncode = returncode
        mock_process.poll.return_value = returncode
        return mock_process

    @patch("src.core.job_executor.subprocess.Popen")
    @patch("builtins.open", new_callable=mock_open)
    @patch("src.core.job_executor.os.makedirs")
    def test_スクリプト成功時に例外が発生しない(self, mock_makedirs, mock_file_open, mock_popen):
        mock_popen.return_value = self._make_mock_process(
            ["line1\n", "line2\n"], returncode=0
        )

        self.executor.execute("echo hello", "/tmp", job_name="test_job")

        mock_popen.assert_called_once()
        call_kwargs = mock_popen.call_args[1]
        assert call_kwargs["shell"] is True
        assert call_kwargs["cwd"] == "/tmp"
        assert call_kwargs["stdout"] == subprocess.PIPE
        assert call_kwargs["stderr"] == subprocess.STDOUT
        assert call_kwargs["text"] is True
        assert call_kwargs["bufsize"] == 1

    @patch("src.core.job_executor.subprocess.Popen")
    @patch("builtins.open", new_callable=mock_open)
    @patch("src.core.job_executor.os.makedirs")
    def test_スクリプト失敗時にScriptExecutionErrorが発生する(
        self, mock_makedirs, mock_file_open, mock_popen
    ):
        mock_popen.return_value = self._make_mock_process(
            ["some output\n", "some error\n"], returncode=1
        )

        with pytest.raises(ScriptExecutionError) as exc_info:
            self.executor.execute("exit 1", "/tmp", job_name="failing_job")

        assert "some output" in exc_info.value.stdout
        assert "some error" in exc_info.value.stdout
        assert exc_info.value.return_code == 1

    @patch("src.core.job_executor.subprocess.Popen")
    @patch("builtins.open", new_callable=mock_open)
    @patch("src.core.job_executor.os.makedirs")
    def test_ログファイルにジョブ名が含まれる(self, mock_makedirs, mock_file_open, mock_popen):
        mock_popen.return_value = self._make_mock_process([], returncode=0)

        self.executor.execute("echo test", "/tmp", job_name="my_job")

        file_path = mock_file_open.call_args[0][0]
        assert "my_job" in file_path

    @patch("src.core.job_executor.subprocess.Popen")
    @patch("builtins.open", new_callable=mock_open)
    @patch("src.core.job_executor.os.makedirs")
    def test_出力が行ごとにログファイルに書き込まれる(
        self, mock_makedirs, mock_file_open, mock_popen
    ):
        mock_popen.return_value = self._make_mock_process(
            ["line1\n", "line2\n", "line3\n"], returncode=0
        )

        self.executor.execute("echo test", "/tmp", job_name="stream_job")

        handle = mock_file_open()
        assert handle.write.call_count == 3
        assert handle.flush.call_count == 3

    @patch("src.core.job_executor.subprocess.Popen")
    @patch("builtins.open", new_callable=mock_open)
    @patch("src.core.job_executor.os.makedirs")
    def test_ScriptExecutionErrorのメッセージに出力が含まれる(
        self, mock_makedirs, mock_file_open, mock_popen
    ):
        mock_popen.return_value = self._make_mock_process(
            ["output text\n"], returncode=2
        )

        with pytest.raises(ScriptExecutionError) as exc_info:
            self.executor.execute("bad_script", "/tmp", job_name="error_job")

        message = str(exc_info.value)
        assert "output text" in message
        assert exc_info.value.return_code == 2

    @patch("src.core.job_executor.subprocess.Popen")
    @patch("builtins.open", new_callable=mock_open)
    @patch("src.core.job_executor.os.makedirs")
    def test_env引数がsubprocessに渡される(self, mock_makedirs, mock_file_open, mock_popen):
        mock_popen.return_value = self._make_mock_process([], returncode=0)

        env = {"CI_BRANCH": "main", "CI_COMMIT_HASH": "abc123"}
        self.executor.execute("echo test", "/tmp", job_name="env_job", env=env)

        call_kwargs = mock_popen.call_args[1]
        # env引数がPopenに渡されていること
        assert "env" in call_kwargs
        process_env = call_kwargs["env"]
        # CI変数がマージされていること
        assert process_env["CI_BRANCH"] == "main"
        assert process_env["CI_COMMIT_HASH"] == "abc123"

    @patch("src.core.job_executor.subprocess.Popen")
    @patch("builtins.open", new_callable=mock_open)
    @patch("src.core.job_executor.os.makedirs")
    def test_envがNoneでもホスト環境変数が渡される(self, mock_makedirs, mock_file_open, mock_popen):
        mock_popen.return_value = self._make_mock_process([], returncode=0)

        self.executor.execute("echo test", "/tmp", job_name="no_env_job", env=None)

        call_kwargs = mock_popen.call_args[1]
        assert "env" in call_kwargs
        # ホスト環境変数のPATHなどが含まれていること
        assert "PATH" in call_kwargs["env"] or "Path" in call_kwargs["env"]

    @patch("src.core.job_executor.os.environ", {"PATH": "/usr/bin", "HOME": "/home/user"})
    @patch("src.core.job_executor.subprocess.Popen")
    @patch("builtins.open", new_callable=mock_open)
    @patch("src.core.job_executor.os.makedirs")
    def test_envがホスト環境変数を上書きできる(self, mock_makedirs, mock_file_open, mock_popen):
        mock_popen.return_value = self._make_mock_process([], returncode=0)

        env = {"PATH": "/custom/bin", "MY_VAR": "value"}
        self.executor.execute("echo test", "/tmp", job_name="override_job", env=env)

        call_kwargs = mock_popen.call_args[1]
        process_env = call_kwargs["env"]
        # 渡した値で上書きされていること
        assert process_env["PATH"] == "/custom/bin"
        assert process_env["MY_VAR"] == "value"
        # ベースのホスト変数も含まれていること
        assert process_env["HOME"] == "/home/user"
