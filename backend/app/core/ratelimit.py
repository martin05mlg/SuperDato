"""Limitador de tasa en memoria (ventana deslizante) por IP y ámbito.

Pensado para un despliegue de un solo proceso (docker compose por defecto). Para
varias réplicas, sustituir `_hits` por un backend compartido (p. ej. Redis).
"""
import threading
import time
from collections import defaultdict, deque
from typing import Callable, Deque, Dict, Tuple

from fastapi import HTTPException, Request, status

from app.core.config import settings

_hits: Dict[Tuple[str, str], Deque[float]] = defaultdict(deque)
_lock = threading.Lock()


def client_ip(request: Request) -> str:
    """IP real del cliente (uvicorn aplica X-Forwarded-For de proxies de confianza)."""
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def reset_rate_limits() -> None:
    with _lock:
        _hits.clear()


def rate_limit(scope: str, max_requests: int, window_seconds: int) -> Callable:
    """Dependencia FastAPI: permite `max_requests` por `window_seconds` e IP en `scope`."""

    async def dependency(request: Request) -> None:
        if not settings.RATE_LIMIT_ENABLED:
            return
        key = (scope, client_ip(request))
        now = time.monotonic()
        with _lock:
            hits = _hits[key]
            while hits and now - hits[0] > window_seconds:
                hits.popleft()
            if len(hits) >= max_requests:
                retry_after = max(1, int(window_seconds - (now - hits[0])))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Demasiadas peticiones. Inténtalo de nuevo en unos minutos.",
                    headers={"Retry-After": str(retry_after)},
                )
            hits.append(now)

    return dependency

