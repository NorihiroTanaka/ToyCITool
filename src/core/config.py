from typing import List, Optional, Dict, Any
import os
import yaml
from pydantic import BaseModel, ConfigDict, Field
from dotenv import load_dotenv

class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    workspace: str = "./workspace"

class DiscordNotificationConfig(BaseModel):
    webhook_url: str = ""
    on_success: bool = True
    on_failure: bool = True

class NotificationsConfig(BaseModel):
    discord: Optional[DiscordNotificationConfig] = None

class GitConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    repo_url: Optional[str] = None
    access_token: Optional[str] = Field(None, alias="accessToken")

class JobConfig(BaseModel):
    name: str
    repo_url: Optional[str] = None
    target_branch: Optional[str] = None
    script: str
    watch_files: List[str] = Field(default_factory=list)
    env: Dict[str, str] = Field(default_factory=dict)
    timeout: Optional[int] = None
    venv: Optional[str] = None

class RepoJobConfig(BaseModel):
    """リポジトリ内の .toyci.yaml から読み込まれるジョブ設定。
    repo_url / target_branch は Webhook ペイロードから自動補完される。
    """
    name: str
    script: str
    watch_files: List[str] = Field(default_factory=list)
    env: Dict[str, str] = Field(default_factory=dict)
    timeout: Optional[int] = None
    venv: Optional[str] = None

class RepoCISettings(BaseModel):
    """リポジトリ内の CI 設定ファイル (.toyci.yaml) のトップレベル構造。"""
    jobs: List[RepoJobConfig] = Field(default_factory=list)

class Settings(BaseModel):
    server: ServerConfig = Field(default_factory=ServerConfig)
    git: GitConfig = Field(default_factory=GitConfig)
    jobs: List[JobConfig] = Field(default_factory=list)
    notifications: Optional[NotificationsConfig] = None
    default_timeout: int = 3600
    max_concurrent_jobs: int = 1

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "Settings":
        """
        設定ファイルを読み込み、Settingsオブジェクトを返す。
        環境変数の展開もサポートする。
        
        読み込み順序：
        1. .envファイルから環境変数を読み込み（存在する場合）
        2. config.yamlを読み込み
        3. 環境変数を展開
        """
        # .envファイルを読み込み（存在する場合のみ、既存の環境変数は上書きしない）
        env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
        env_path = os.path.normpath(env_path)
        
        if os.path.exists(env_path):
            load_dotenv(env_path, override=False)
        
        # 既存のconfig.yaml読み込み処理
        path = config_path or os.environ.get("TOYCI_CONFIG_PATH", "config.yaml")
        
        if not os.path.exists(path):
            return cls()

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            # 環境変数を展開 (${VAR} 形式)
            content = os.path.expandvars(content)
            data = yaml.safe_load(content) or {}
            
        return cls(**data)
