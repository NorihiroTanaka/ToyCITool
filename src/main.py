import argparse
import logging
import uvicorn
from .core import load_config
from .api import app

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
    )

    parser = argparse.ArgumentParser(description="ToyCI Server")
    parser.add_argument("-a", "--address", help="Host address to bind to", default=None)
    parser.add_argument("-p", "--port", help="Port to bind to", type=int, default=None)
    args = parser.parse_args()

    config = load_config()
    server_conf = config.get("server", {})

    host = args.address if args.address else server_conf.get("host", "0.0.0.0")
    port = args.port if args.port else server_conf.get("port", 8000)

    uvicorn.run("src.api:app", host=host, port=port, reload=True)
