import logging

from fastapi import status, FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import SERVICE_TOKEN


ALLOWED_PATH_WITHOUT_AUTH = ["/docs", "/openapi.json"]


class AuthValidationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: callable):
        logging.debug("Got request: method=%s, url=%s, headers=%s", request.method, request.url, request.headers)
        if request.url.path in ALLOWED_PATH_WITHOUT_AUTH:
            logging.debug("Got allowed request path")
            return await call_next(request)
        if token := request.headers.get("X-Auth-Token", None):
            if token != SERVICE_TOKEN:
                logging.error("Got invalid token: %s", token)
                return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"detail": "Forbidden"})
        else:
            logging.debug("Got no token")
            return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": "Unauthorized"})
        response = await call_next(request)
        return response
