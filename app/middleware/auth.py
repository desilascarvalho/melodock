from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

_OPEN_PATHS = {"/health", "/ws", "/docs", "/openapi.json", "/redoc"}


class ApiKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        password = settings.ACCESS_PASSWORD
        if not password:
            return await call_next(request)

        path = request.url.path
        if not path.startswith("/api") or path in _OPEN_PATHS:
            return await call_next(request)

        provided = request.headers.get("X-Melodock-Key", "")
        if provided != password:
            return JSONResponse(
                status_code=401,
                content={"error": "Unauthorized", "code": 401},
            )

        return await call_next(request)
