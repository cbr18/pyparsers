from __future__ import annotations

from typing import Iterable

import async_api_server


COMMON_PATHS = {"/", "/health", "/docs", "/redoc", "/openapi.json"}
SOURCE_PREFIXES = {
    "dongchedi": ("/cars/dongchedi", "/update/dongchedi", "/blocked/dongchedi"),
    "che168": ("/cars/che168", "/che168/detailed", "/blocked/che168"),
}


def _is_allowed_path(path: str, prefixes: Iterable[str]) -> bool:
    if path in COMMON_PATHS:
        return True
    return any(path.startswith(prefix) for prefix in prefixes)


def build_source_app(source: str):
    if source not in SOURCE_PREFIXES:
        raise ValueError(f"Unsupported source: {source}")

    app = async_api_server.app
    prefixes = SOURCE_PREFIXES[source]
    app.router.routes = [
        route
        for route in app.router.routes
        if _is_allowed_path(getattr(route, "path", ""), prefixes)
    ]
    app.openapi_schema = None
    app.title = f"{app.title} ({source})"
    return app
