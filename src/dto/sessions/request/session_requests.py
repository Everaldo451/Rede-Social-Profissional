from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class UserIdRequest(BaseModel):
    user_id: str = Field(min_length=1)


class SessionIdRequest(BaseModel):
    session_id: str = Field(min_length=1)


class RevokeSessionRequest(SessionIdRequest):
    reference: str = Field(pattern=r"^[0-9a-f]{64}$")
