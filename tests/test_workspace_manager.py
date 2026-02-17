"""WorkspaceManagerのテスト。"""

import os
import tempfile
from unittest.mock import patch

import pytest

from src.core.workspace_manager import WorkspaceManager
from src.core.exceptions import WorkspaceError, WorkspaceCleanupError


class TestWorkspaceManagerPrepare:
    """prepare_workspace のテスト。"""

    def test_新規ディレクトリが作成される(self, tmp_path):
        manager = WorkspaceManager(base_dir=str(tmp_path))
        work_dir = manager.prepare_workspace("test_job")
        assert os.path.isdir(work_dir)
        assert work_dir == os.path.join(str(tmp_path), "test_job")

    def test_既存ディレクトリが削除されてから作成される(self, tmp_path):
        manager = WorkspaceManager(base_dir=str(tmp_path))
        # 先にディレクトリとファイルを作成
        job_dir = os.path.join(str(tmp_path), "test_job")
        os.makedirs(job_dir)
        marker = os.path.join(job_dir, "marker.txt")
        with open(marker, "w") as f:
            f.write("test")

        work_dir = manager.prepare_workspace("test_job")
        assert os.path.isdir(work_dir)
        # 古いファイルは削除されていること
        assert not os.path.exists(marker)

    @patch("src.core.workspace_manager.shutil.rmtree", side_effect=PermissionError("access denied"))
    def test_削除失敗時にWorkspaceErrorが発生する(self, mock_rmtree, tmp_path):
        manager = WorkspaceManager(base_dir=str(tmp_path))
        # 既存ディレクトリを作成
        job_dir = os.path.join(str(tmp_path), "test_job")
        os.makedirs(job_dir)

        with pytest.raises(WorkspaceError):
            manager.prepare_workspace("test_job")


class TestWorkspaceManagerCleanup:
    """cleanup_workspace のテスト。"""

    def test_ディレクトリが削除される(self, tmp_path):
        manager = WorkspaceManager(base_dir=str(tmp_path))
        job_dir = os.path.join(str(tmp_path), "test_job")
        os.makedirs(job_dir)

        manager.cleanup_workspace("test_job")
        assert not os.path.exists(job_dir)

    def test_存在しないディレクトリに対してエラーにならない(self, tmp_path):
        manager = WorkspaceManager(base_dir=str(tmp_path))
        # 例外が発生しないこと
        manager.cleanup_workspace("nonexistent_job")

    @patch("src.core.workspace_manager.shutil.rmtree", side_effect=PermissionError("access denied"))
    def test_最大リトライ後にWorkspaceCleanupErrorが発生する(self, mock_rmtree, tmp_path):
        manager = WorkspaceManager(base_dir=str(tmp_path))
        job_dir = os.path.join(str(tmp_path), "test_job")
        os.makedirs(job_dir)

        with pytest.raises(WorkspaceCleanupError):
            manager.cleanup_workspace("test_job")

        # 3回リトライされたこと
        assert mock_rmtree.call_count == 3
