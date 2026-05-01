from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple rate limiter. Replace with Redis-backed solution for production."""

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        # TODO: Implement token-bucket or sliding window rate limiting
        return await call_next(request)
