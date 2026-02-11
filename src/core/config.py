from typing import List, Optional, Dict, Any
import os
import yaml
from pydantic import BaseModel, Field

class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    workspace: str = "./workspace"

class GitConfig(BaseModel):
    repo_url: Optional[str] = None
    accessToken: Optional[str] = None

class JobConfig(BaseModel):
    name: str
    repo_url: Optional[str] = None
    target_branch: Optional[str] = None
    script: str
    watch_files: List[str] = Field(default_factory=list)

class Settings(BaseModel):
    server: ServerConfig = Field(default_factory=ServerConfig)
    git: GitConfig = Field(default_factory=GitConfig)
    jobs: List[JobConfig] = Field(default_factory=list)
    
    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "Settings":
        """
        設定ファイルを読み込み、Settingsオブジェクトを返す。
        環境変数の展開もサポートする。
        """
        path = config_path or os.environ.get("TOYCI_CONFIG_PATH", "config.yaml")
        
        if not os.path.exists(path):
            return cls()

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            # 環境変数を展開 (${VAR} 形式)
            content = os.path.expandvars(content)
            data = yaml.safe_load(content) or {}
            
        return cls(**data)
