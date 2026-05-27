"""
uvicorn_cli: starts uvicorn via CLI with --log-config pointing to amox's config.

Proves that `uvicorn --log-config config.json` produces structured log output.
The script points --log-config at amox's shipped dictConfig.json, starts
uvicorn as a subprocess, waits for it to accept connections, then terminates.
"""

import importlib.resources
import pathlib
import socket
import subprocess
import sys
import time

import uvicorn

import amox

from . import uvicorn_log_config

HOST = "127.0.0.1"


def find_free_port() -> int:
    """Bind to port 0 and return the OS-assigned free port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((HOST, 0))
        (_, port) = sock.getsockname()
        return port


SCRIPTS_DIR = pathlib.Path(__file__).parent

LOG_CONFIG = importlib.resources.files(amox.__name__) / "dictConfig.json"
"""
../../../src/amox/dictConfig.json
"""


def wait_for_server(host: str, port: int, timeout: float = 4.0) -> None:
    """Poll until the server accepts TCP connections."""
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.08)
            if sock.connect_ex((host, port)) == 0:
                return
        time.sleep(0.04)
    msg = f"Server at {host}:{port} did not start within {timeout}s"
    raise TimeoutError(msg)


if __name__ == "__main__":
    port = find_free_port()

    proc = subprocess.Popen(  # noqa: S603
        [
            sys.executable,
            "-m",
            uvicorn.__name__,
            "--log-config",
            f"{LOG_CONFIG}",
            "--app-dir",
            f"{SCRIPTS_DIR}",
            "--host",
            HOST,
            "--port",
            f"{port}",
            "--lifespan",
            "off",
            f"{uvicorn_log_config.__name__}:{uvicorn_log_config.app.__name__}",
        ],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    wait_for_server(HOST, port)
    proc.terminate()
    _, stderr = proc.communicate(timeout=4)
    _ = sys.stderr.write(stderr)
