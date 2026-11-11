import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.integrations.payments.base import PaymentMethod


class PaymentCreate(BaseModel):
    method: PaymentMethod


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    booking_id: uuid.UUID
    method: Literal["card", "kaspi"]
    amount_kzt: int
    status: Literal["pending", "succeeded", "failed", "refunded"]
    redirect_url: str | None
