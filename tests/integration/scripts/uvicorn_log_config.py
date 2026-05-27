"""
uvicorn_log_config: starts uvicorn with amox's config, shuts down after startup.

Proves that `uvicorn.run(log_config=config())` produces structured log output
from uvicorn's internal loggers.
"""

import socket
import typing as t

import uvicorn
from uvicorn._types import ASGIReceiveCallable, ASGISendCallable, Scope

from amox import config


class AutoShutdownServer(uvicorn.Server):
    """Auto closing ASGI Server."""

    @t.override
    async def startup(self, sockets: list[socket.socket] | None = None) -> None:
        """Trigger shutdown on startup."""
        await super().startup(sockets)
        self.should_exit: bool = True


async def app(
    scope: Scope,
    receive: ASGIReceiveCallable,
    send: ASGISendCallable,
) -> None:
    """AGI Application. Lifespan listener exlusive."""
    if scope["type"] == "lifespan":
        message = await receive()
        if message["type"] == "lifespan.startup":
            await send({"type": "lifespan.startup.complete"})
        message = await receive()
        if message["type"] == "lifespan.shutdown":
            await send({"type": "lifespan.shutdown.complete"})


if __name__ == "__main__":
    cfg = uvicorn.Config(app, log_config=config(), lifespan="on")  # ty: ignore[invalid-argument-type]  # pyright: ignore[reportArgumentType]
    server = AutoShutdownServer(cfg)
    server.run()
