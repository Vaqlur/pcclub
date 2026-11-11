from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field

from app.domain.phone import normalize_phone

Phone = Annotated[
    str, Field(max_length=32, examples=["+77071234567"]), AfterValidator(normalize_phone)
]


class OtpRequest(BaseModel):
    phone: Phone


class OtpVerify(BaseModel):
    phone: Phone
    code: str = Field(pattern=r"^\d{6}$", examples=["000000"])


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=16, max_length=200)


class StaffLogin(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=200)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until the access token expires
