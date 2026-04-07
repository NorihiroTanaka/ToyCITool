"""RepoCIConfigLoader のテスト。"""

import os
import textwrap

import pytest

from src.core.repo_ci_config_loader import RepoCIConfigLoader, REPO_CI_CONFIG_FILE


@pytest.fixture
def loader():
    return RepoCIConfigLoader()


class TestRepoCIConfigLoaderLoadFromPath:
    def test_設定ファイルが存在する場合に設定が返る(self, tmp_path, loader):
        config_file = tmp_path / REPO_CI_CONFIG_FILE
        config_file.write_text(
            textwrap.dedent("""\
                jobs:
                  - name: build
                    script: make build
                    watch_files:
                      - "src/*.py"
            """),
            encoding="utf-8",
        )
        result = loader.load_from_path(str(tmp_path))

        assert result is not None
        assert len(result.jobs) == 1
        assert result.jobs[0].name == "build"
        assert result.jobs[0].script == "make build"
        assert result.jobs[0].watch_files == ["src/*.py"]

    def test_設定ファイルがない場合はNoneが返る(self, tmp_path, loader):
        result = loader.load_from_path(str(tmp_path))
        assert result is None

    def test_複数ジョブを読み込める(self, tmp_path, loader):
        config_file = tmp_path / REPO_CI_CONFIG_FILE
        config_file.write_text(
            textwrap.dedent("""\
                jobs:
                  - name: test
                    script: pytest
                  - name: lint
                    script: flake8
                    env:
                      MAX_LINE: "120"
                    timeout: 300
            """),
            encoding="utf-8",
        )
        result = loader.load_from_path(str(tmp_path))

        assert result is not None
        assert len(result.jobs) == 2
        assert result.jobs[1].env == {"MAX_LINE": "120"}
        assert result.jobs[1].timeout == 300

    def test_不正なYAMLの場合はNoneが返る(self, tmp_path, loader):
        config_file = tmp_path / REPO_CI_CONFIG_FILE
        config_file.write_text("jobs: [invalid: yaml: content:", encoding="utf-8")
        result = loader.load_from_path(str(tmp_path))
        assert result is None

    def test_空ファイルの場合はジョブが空のSettingsが返る(self, tmp_path, loader):
        config_file = tmp_path / REPO_CI_CONFIG_FILE
        config_file.write_text("", encoding="utf-8")
        result = loader.load_from_path(str(tmp_path))
        assert result is not None
        assert result.jobs == []
