import os
import yaml
from typing import Dict, Any, Optional

class ConfigLoader:
    def __init__(self, config_path: Optional[str] = None):
        if config_path:
            self.config_path = config_path
        else:
            self.config_path = os.environ.get("TOYCI_CONFIG_PATH", "config.yaml")

    def load(self) -> Dict[str, Any]:
        """設定ファイルを読み込む"""
        if not os.path.exists(self.config_path):
            return {"server": {}, "jobs": []}
        with open(self.config_path, "r") as f:
            content = f.read()
            # 環境変数を展開 (${VAR} 形式)
            content = os.path.expandvars(content)
            return yaml.safe_load(content)

# Backward compatibility function
def load_config(path: Optional[str] = None) -> Dict[str, Any]:
    return ConfigLoader(path).load()
