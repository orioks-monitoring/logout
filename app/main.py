import logging

from fastapi import status, FastAPI, HTTPException
from pydantic import PositiveInt, BaseModel

from app.managers import reset_user
from app.middlewares import AuthValidationMiddleware
from app.models.users import UserStatus, UserNotifySettings


app = FastAPI()
app.add_middleware(AuthValidationMiddleware)


class User(BaseModel):
    user_telegram_id: PositiveInt
    agreement_accepted: bool
    authenticated: bool
    login_attempt_count: int
    failed_request_count: int

    class Config:
        from_attributes = True


class UserNotify(BaseModel):
    user_telegram_id: PositiveInt
    marks: bool
    news: bool
    homeworks: bool
    requests: bool

    class Config:
        from_attributes = True


class UserAndNotify(BaseModel):
    user: User
    notify: UserNotify

    class Config:
        from_attributes = True


@app.get("/user/{user_telegram_id}")
async def get_user_status(user_telegram_id: PositiveInt) -> User:
    logging.info(f"Get user status for user with id: %s", user_telegram_id)
    user = UserStatus.find_one(user_telegram_id=user_telegram_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return User(**user.as_dict())


@app.post("/user/{user_telegram_id}/logout")
async def logout_user(user_telegram_id: PositiveInt) -> UserAndNotify:
    logging.info(f"Logout user with id: %s", user_telegram_id)

    user = UserStatus.find_one(user_telegram_id=user_telegram_id)
    user_settings = UserNotifySettings.find_one(user_telegram_id=user_telegram_id)

    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user_settings is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User settings not found")

    logging.debug("Resetting user %s...", user)
    reset_user(user, user_settings, user_telegram_id)
    logging.info("User %s reset", user)

    return UserAndNotify(user=User(**user.as_dict()), notify=UserNotify(**user_settings.as_dict()))
