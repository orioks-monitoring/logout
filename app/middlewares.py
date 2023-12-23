import logging

from fastapi import FastAPI, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import LOGIN_LOGOUT_SERVICE_HEADER_NAME, LOGIN_LOGOUT_SERVICE_TOKEN

ALLOWED_PATH_WITHOUT_AUTH = ["/docs", "/openapi.json", "/health"]


logger = logging.getLogger(__name__)


class AuthValidationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: callable):
        logger.debug(
            "Got request: method=%s, url=%s, headers=%s",
            request.method,
            request.url,
            request.headers,
        )
        if request.url.path in ALLOWED_PATH_WITHOUT_AUTH:
            logger.debug("Got allowed request path")
            return await call_next(request)
        if token := request.headers.get(LOGIN_LOGOUT_SERVICE_HEADER_NAME, None):
            if token != LOGIN_LOGOUT_SERVICE_TOKEN:
                logger.error("Got invalid token: %s", token)
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Forbidden"},
                )
        else:
            logger.debug("Got no token")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Unauthorized"},
            )
        response = await call_next(request)
        return response
