from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.common import ORMModel


class InventoryItemBase(ORMModel):
    name: str = Field(min_length=2, max_length=200)
    sku: str = Field(min_length=1, max_length=100)
    quantity_available: int = Field(default=0, ge=0, le=10_000_000)

    @field_validator("name", "sku")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("sku")
    @classmethod
    def normalise_sku(cls, value: str) -> str:
        return value.strip().upper()


class InventoryItemCreate(InventoryItemBase):
    pass


class InventoryItemUpdate(ORMModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    sku: str | None = Field(default=None, min_length=1, max_length=100)
    quantity_available: int | None = Field(default=None, ge=0, le=10_000_000)

    @field_validator("name", "sku")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else value

    @field_validator("sku")
    @classmethod
    def normalise_sku(cls, value: str | None) -> str | None:
        return value.strip().upper() if value is not None else value


class InventoryItemRead(ORMModel):
    id: UUID
    name: str
    sku: str
    quantity_available: int
    created_at: datetime
    updated_at: datetime
