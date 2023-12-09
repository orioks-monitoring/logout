from pydantic import BaseModel, PositiveInt


class UserStatusSchema(BaseModel):
    user_telegram_id: PositiveInt
    agreement_accepted: bool
    authenticated: bool
    login_attempt_count: int
    failed_request_count: int

    model_config = {"from_attributes": True}


class UserStatusAuthenticatedSchema(BaseModel):
    user_telegram_id: PositiveInt
    authenticated: bool

    model_config = {"from_attributes": True}


class UserLoginBodySchema(BaseModel):
    cookies: dict[str, str]

    model_config = {"from_attributes": True}
