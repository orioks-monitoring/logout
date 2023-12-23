from fastapi import FastAPI

from app.middlewares import AuthValidationMiddleware
from app.routers import user_router
from app.schemas import AppStatusSchema

app = FastAPI(
    title="Logout service",
    description="Service for logout user from system.",
)

app.add_middleware(AuthValidationMiddleware)
app.include_router(user_router)


@app.get("/health", tags=["internal"])
async def health() -> AppStatusSchema:
    return AppStatusSchema(status="UP")
