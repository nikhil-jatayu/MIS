from __future__ import annotations

from typing import Any, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.schemas.common import Page, page_count

T = TypeVar("T")


def paginate(
    db: Session,
    statement: Select[Any],
    *,
    page: int,
    page_size: int,
) -> tuple[list[Any], int]:
    page = max(page, 1)
    page_size = max(min(page_size, 100), 1)
    count_statement = select(func.count()).select_from(
        statement.order_by(None).limit(None).offset(None).subquery()
    )
    total = int(db.scalar(count_statement) or 0)
    items = list(
        db.scalars(statement.offset((page - 1) * page_size).limit(page_size)).unique().all()
    )
    return items, total


def build_page(items: list[T], total: int, page: int, page_size: int) -> Page[T]:
    return Page[T](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=page_count(total, page_size),
    )
