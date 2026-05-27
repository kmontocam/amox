"""
uvicorn_access: starts uvicorn, handles one HTTP request, shuts down.

Proves that uvicorn's access logs are structured through amox's formatter.
"""

import socket
import sys
import typing as t
from http import HTTPStatus

import uvicorn
from uvicorn._types import ASGIReceiveCallable, ASGISendCallable, Scope

from amox import config

HOST = "127.0.0.1"
PORT = 8000
READY_SIGNAL = "READY"
HTTP_STATUS_RESPONSE_CODE = HTTPStatus.NO_CONTENT


class StatefulServer(uvicorn.Server):
    """
    ASGI Server with a reference to itself on lifespan's state.

    Additionally includes readiness process signal to communicate server is ready to
    process requests.
    """

    @t.override
    async def startup(self, sockets: list[socket.socket] | None = None) -> None:
        """Inject server reference into app state, then signal readiness to parent."""
        await super().startup(sockets)
        state: dict[str, uvicorn.Server] = self.lifespan.state
        state["server"] = self
        _ = sys.stdout.write(f"{READY_SIGNAL}\n")
        _ = sys.stdout.flush()


async def app(
    scope: Scope,
    receive: ASGIReceiveCallable,
    send: ASGISendCallable,
) -> None:
    """AGI Application. Lifespan listener, with shutdown on any HTTP Request."""
    if scope["type"] == "lifespan":
        message = await receive()
        if message["type"] == "lifespan.startup":
            await send({"type": "lifespan.startup.complete"})
        message = await receive()
        if message["type"] == "lifespan.shutdown":
            await send({"type": "lifespan.shutdown.complete"})
    elif scope["type"] == "http":
        _ = await receive()
        await send(
            {
                "type": "http.response.start",
                "status": HTTP_STATUS_RESPONSE_CODE,
                "headers": [],
            },
        )
        await send({"type": "http.response.body", "body": b""})
        state: dict[str, uvicorn.Server] = scope.get("state", {})
        server: uvicorn.Server = state["server"]
        server.should_exit = True


if __name__ == "__main__":
    cfg = uvicorn.Config(app, host=HOST, port=PORT, log_config=config(), lifespan="on")  # ty: ignore[invalid-argument-type]  # pyright: ignore[reportArgumentType]
    server = StatefulServer(cfg)
    server.run()
