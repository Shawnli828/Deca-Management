#!/usr/bin/env python3
"""Local server entrypoint and legacy import compatibility layer."""

import os
import socket
import sys
import webbrowser

from server_modules.app_runtime import DB_PATH, init_db, using_postgres
from server_modules.legacy_server_exports import *  # noqa: F401,F403


def find_open_port(start_port=8765):
    for port in range(start_port, start_port + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError("No available local port found.")


def run_fastapi_server():
    sys.modules.setdefault("server", sys.modules[__name__])

    try:
        import uvicorn
    except ImportError as error:
        raise RuntimeError("uvicorn is required to run the local API server. Run: pip install -r requirements.txt") from error

    init_db()
    cloud_port = os.environ.get("PORT", "").strip()
    port = int(cloud_port) if cloud_port else find_open_port()
    host = "0.0.0.0" if cloud_port else "127.0.0.1"
    url = f"http://127.0.0.1:{port}/" if not cloud_port else f"http://{host}:{port}/"
    print(f"Management Table is running: {url}")
    print(f"Database backend: {'Postgres' if using_postgres() else f'SQLite ({DB_PATH})'}")
    print("API framework: FastAPI")
    if not cloud_port:
        webbrowser.open(url)
    uvicorn.run("api.index:app", host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_fastapi_server()
