import argparse
import uvicorn
import os
from .core.config import Settings
from .core.logging_config import setup_logging

if __name__ == "__main__":
    if not os.path.exists("log"):
        os.makedirs("log")

    parser = argparse.ArgumentParser(description="ToyCI Server")
    parser.add_argument("-a", "--address", help="Host address to bind to", default=None)
    parser.add_argument("-p", "--port", help="Port to bind to", type=int, default=None)
    args = parser.parse_args()

    # 初期設定ロード (Settingsクラスを使用)
    settings = Settings.load()
    
    # ログ設定がファイルに依存している場合の互換性維持、またはSettingsから取得するように改修
    # ここでは既存の setup_logging を呼び出す（logging.yamlがあれば使う）
    setup_logging()

    host = args.address if args.address else settings.server.host
    port = args.port if args.port else settings.server.port

    print(f"Starting server at http://{host}:{port}")

    # uvicornのlog_config引数は、logging.yamlが存在する場合のみ指定する
    # 監視対象をsrc配下と設定ファイルに限定する
    reload_includes = ["src/**", "config.yaml", "logging.yaml"]

    if os.path.exists("logging.yaml"):
        uvicorn.run(
            "src.api:app",
            host=host,
            port=port,
            reload=True,
            reload_includes=reload_includes,
            log_config="logging.yaml",
        )
    else:
        uvicorn.run(
            "src.api:app",
            host=host,
            port=port,
            reload=True,
            reload_includes=reload_includes,
        )
