import logging
import logging.config
import yaml
import os

def setup_logging(config_path: str = "logging.yaml", log_dir: str = "log"):
    """
    アプリケーションのログ設定をロードします。

    Args:
        config_path (str): ログ設定ファイル(YAML)へのパス。
        log_dir (str): ログ出力先ディレクトリ。存在しない場合は作成されます。
    """
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            log_config = yaml.safe_load(f)
            logging.config.dictConfig(log_config)
            logging.info(f"Logging configuration loaded from {config_path}")
    else:
        logging.basicConfig(level=logging.INFO)
        logging.warning(f"{config_path} not found, using basic config")
