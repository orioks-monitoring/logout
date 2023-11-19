from pydantic import BaseModel, PositiveInt


class User(BaseModel):
    user_telegram_id: PositiveInt
    agreement_accepted: bool
    authenticated: bool
    login_attempt_count: int
    failed_request_count: int

    model_config = {"from_attributes": True}


class UserNotify(BaseModel):
    user_telegram_id: PositiveInt
    marks: bool
    news: bool
    homeworks: bool
    requests: bool

    model_config = {"from_attributes": True}


class UserAndNotify(BaseModel):
    user: User
    notify: UserNotify

    model_config = {"from_attributes": True}
