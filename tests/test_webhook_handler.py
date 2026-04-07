"""GitHubProvider のテスト。"""

import pytest

from src.core.webhook_handler import GitHubProvider


class TestGitHubProviderGetProviderId:
    def test_githubが返る(self):
        provider = GitHubProvider()
        assert provider.get_provider_id() == "github"


class TestGitHubProviderShouldSkip:
    def setup_method(self):
        self.provider = GitHubProvider()

    def test_skip_ciを含む場合にTrueが返る(self):
        payload = {"head_commit": {"message": "update [skip ci] readme"}}
        assert self.provider.should_skip(payload) is True

    def test_skip_ci_ブラケットなしでもTrueが返る(self):
        payload = {"head_commit": {"message": "update skip ci readme"}}
        assert self.provider.should_skip(payload) is True

    def test_通常のメッセージの場合にFalseが返る(self):
        payload = {"head_commit": {"message": "fix bug in login"}}
        assert self.provider.should_skip(payload) is False

    def test_head_commitが存在しない場合にFalseが返る(self):
        payload = {}
        assert self.provider.should_skip(payload) is False

    def test_大文字小文字を区別しない(self):
        payload = {"head_commit": {"message": "[SKIP CI] deploy"}}
        assert self.provider.should_skip(payload) is True


class TestGitHubProviderCanHandle:
    def setup_method(self):
        self.provider = GitHubProvider()

    def test_x_github_eventヘッダがある場合にTrueが返る(self):
        headers = {"x-github-event": "push"}
        assert self.provider.can_handle(headers) is True

    def test_大文字のX_GitHub_Eventでも動作する(self):
        headers = {"X-GitHub-Event": "push"}
        assert self.provider.can_handle(headers) is True

    def test_GitHubヘッダがない場合にFalseが返る(self):
        headers = {"content-type": "application/json"}
        assert self.provider.can_handle(headers) is False


class TestGitHubProviderExtractChangedFiles:
    def setup_method(self):
        self.provider = GitHubProvider()

    def test_added_modified_removedが全て含まれる(self, mock_github_payload):
        result = self.provider.extract_changed_files(mock_github_payload)
        assert "new_file.py" in result
        assert "src/main.py" in result
        assert "requirements.txt" in result
        assert "old_file.txt" in result

    def test_commitsが空の場合に空セットが返る(self):
        payload = {"commits": []}
        assert self.provider.extract_changed_files(payload) == set()

    def test_commitsキーがない場合に空セットが返る(self):
        payload = {}
        assert self.provider.extract_changed_files(payload) == set()

    def test_重複ファイルが重複なく返る(self):
        payload = {
            "commits": [
                {"added": ["file.py"], "modified": ["file.py"], "removed": []},
                {"added": [], "modified": ["file.py"], "removed": []},
            ]
        }
        result = self.provider.extract_changed_files(payload)
        assert result == {"file.py"}


class TestGitHubProviderExtractRepoInfo:
    def setup_method(self):
        self.provider = GitHubProvider()

    def test_clone_urlとブランチが返る(self):
        payload = {
            "ref": "refs/heads/main",
            "repository": {"clone_url": "https://github.com/owner/repo.git"},
        }
        result = self.provider.extract_repo_info(payload)
        assert result == {
            "repo_url": "https://github.com/owner/repo.git",
            "branch": "main",
        }

    def test_clone_urlがない場合はhtml_urlにフォールバックする(self):
        payload = {
            "ref": "refs/heads/develop",
            "repository": {"html_url": "https://github.com/owner/repo"},
        }
        result = self.provider.extract_repo_info(payload)
        assert result["repo_url"] == "https://github.com/owner/repo"
        assert result["branch"] == "develop"

    def test_repositoryキーがない場合はNoneが返る(self):
        payload = {"ref": "refs/heads/main"}
        assert self.provider.extract_repo_info(payload) is None

    def test_refキーがない場合はNoneが返る(self):
        payload = {"repository": {"clone_url": "https://github.com/owner/repo.git"}}
        assert self.provider.extract_repo_info(payload) is None

    def test_refs_heads_プレフィックスが除去される(self):
        payload = {
            "ref": "refs/heads/feature/my-branch",
            "repository": {"clone_url": "https://github.com/owner/repo.git"},
        }
        result = self.provider.extract_repo_info(payload)
        assert result["branch"] == "feature/my-branch"


class TestGitHubProviderGetPayloadMeta:
    def setup_method(self):
        self.provider = GitHubProvider()

    def test_最後のコミット情報が返る(self):
        payload = {
            "commits": [
                {"id": "first", "message": "first commit"},
                {"id": "last", "message": "last commit"},
            ]
        }
        result = self.provider.get_payload_meta(payload)
        assert result["id"] == "last"

    def test_commitsが空の場合に空辞書が返る(self):
        payload = {"commits": []}
        assert self.provider.get_payload_meta(payload) == {}

    def test_commitsキーがない場合に空辞書が返る(self):
        payload = {}
        assert self.provider.get_payload_meta(payload) == {}
