"""Login request/response. Not in the SRS story list, but implied by
'Preconditions: Caller is authenticated' on US-01-01 and US-01-03."""

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
