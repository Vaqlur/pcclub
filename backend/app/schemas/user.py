import uuid
from datetime import date
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class UserOut(BaseModel):
    id: uuid.UUID
    phone: str
    first_name: str | None
    last_name: str | None
    birth_date: date | None
    identity_status: str
    iin_masked: str | None  # the full IIN is never returned


class UserUpdate(BaseModel):
    first_name: Name | None = None
    last_name: Name | None = None


class IdentitySubmit(BaseModel):
    iin: str = Field(min_length=12, max_length=12, examples=["900101300007"])
    first_name: Name
    last_name: Name
