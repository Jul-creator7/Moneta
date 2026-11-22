from datetime import date
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StringConstraints

from .community_schemas import CommunityTime


def uppercase(value: object) -> object:
    return value.upper() if isinstance(value, str) else value


def compact_serial(value: object) -> object:
    if isinstance(value, str):
        return "".join(value.upper().split()).replace("-", "")
    return value


def normalize_series(value: object) -> object:
    return " ".join(value.upper().split()) if isinstance(value, str) else value


class BanknoteIdentity(BaseModel):
    currency: Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[A-Z]{3}$"), BeforeValidator(uppercase)]
    denomination: int = Field(strict=True, gt=0, le=1_000_000)
    serial_number: Annotated[str, StringConstraints(pattern=r"^[A-Z0-9]{3,32}$"), BeforeValidator(compact_serial)]
    series: Annotated[str, StringConstraints(max_length=40), BeforeValidator(normalize_series)] = ""


class EventInput(BaseModel):
    request_id: UUID
    city: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
    is_hidden: bool = Field(strict=True)


class EventRequest(BaseModel):
    note: BanknoteIdentity
    event: EventInput


class BanknoteEventView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    city: str
    message: str
    is_hidden: bool
    created_at: CommunityTime


class BanknoteStory(BaseModel):
    note: BanknoteIdentity
    events: list[BanknoteEventView]
    before_id: int | None


class DealView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    store: str
    product: str
    category: str
    city: str
    currency: str
    original_minor: int
    sale_minor: int
    latitude: float
    longitude: float
    expires_on: date | None
