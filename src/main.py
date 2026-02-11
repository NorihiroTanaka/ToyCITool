import argparse
import uvicorn
import os
from .core import load_config

if __name__ == "__main__":
    if not os.path.exists("log"):
        os.makedirs("log")

    parser = argparse.ArgumentParser(description="ToyCI Server")
    parser.add_argument("-a", "--address", help="Host address to bind to", default=None)
    parser.add_argument("-p", "--port", help="Port to bind to", type=int, default=None)
    args = parser.parse_args()

    config = load_config()
    server_conf = config.get("server", {})

    host = args.address if args.address else server_conf.get("host", "0.0.0.0")
    port = args.port if args.port else server_conf.get("port", 8000)

    if os.path.exists("logging.yaml"):
        uvicorn.run("src.api:app", host=host, port=port, reload=True, log_config="logging.yaml")
    else:
        uvicorn.run("src.api:app", host=host, port=port, reload=True)
