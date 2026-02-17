"""テスト用の共通フィクスチャ。"""

import pytest

from src.core.config import Settings, GitConfig, JobConfig


@pytest.fixture
def mock_settings():
    """テスト用のSettings。"""
    return Settings(
        git=GitConfig(access_token="test_token", repo_url="https://github.com/example/default.git"),
        jobs=[
            JobConfig(
                name="test_job",
                repo_url="https://github.com/example/repo.git",
                target_branch="main",
                script="echo hello",
                watch_files=["src/*.py", "requirements.txt"],
            )
        ],
    )


@pytest.fixture
def mock_github_payload():
    """テスト用のGitHub Webhookペイロード。"""
    return {
        "ref": "refs/heads/main",
        "head_commit": {
            "id": "abc123",
            "message": "Update README",
        },
        "commits": [
            {
                "id": "abc123",
                "message": "Update README",
                "added": ["new_file.py"],
                "modified": ["src/main.py", "requirements.txt"],
                "removed": ["old_file.txt"],
            }
        ],
    }


@pytest.fixture
def mock_github_headers():
    """テスト用のGitHubリクエストヘッダー。"""
    return {
        "x-github-event": "push",
        "content-type": "application/json",
    }
