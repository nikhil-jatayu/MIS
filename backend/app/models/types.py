from __future__ import annotations

from enum import StrEnum

from sqlalchemy import Enum as SAEnum


def enum_type(enum_class: type[StrEnum], name: str, length: int = 40) -> SAEnum:
    """Store enums as validated VARCHAR values instead of native PG enums."""
    return SAEnum(
        enum_class,
        name=name,
        native_enum=False,
        length=length,
        validate_strings=True,
        values_callable=lambda members: [member.value for member in members],
    )
