from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID


class UserRole(StrEnum):
    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"
    USER = "USER"


class ProjectType(StrEnum):
    RND = "RND"
    PRODUCTION = "PRODUCTION"


class ProjectStatus(StrEnum):
    PENDING_INVENTORY = "PENDING_INVENTORY"
    READY_FOR_PRODUCTION = "READY_FOR_PRODUCTION"
    AWAITING_DELIVERY = "AWAITING_DELIVERY"
    IN_PRODUCTION = "IN_PRODUCTION"
    IN_TESTING = "IN_TESTING"
    COMPLETED = "COMPLETED"


class Priority(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ProjectMemberRole(StrEnum):
    DEVELOPER = "DEVELOPER"
    PRODUCER = "PRODUCER"
    TESTER = "TESTER"


class PurchaseRequestStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ORDERED = "ORDERED"
    DELIVERED = "DELIVERED"


class AlertType(StrEnum):
    STANDARD = "STANDARD"
    ESCALATED = "ESCALATED"


class TestResult(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"


ACTIVE_PROJECT_STATUSES = {
    ProjectStatus.PENDING_INVENTORY,
    ProjectStatus.READY_FOR_PRODUCTION,
    ProjectStatus.AWAITING_DELIVERY,
    ProjectStatus.IN_PRODUCTION,
    ProjectStatus.IN_TESTING,
}

OPEN_PURCHASE_STATUSES = {
    PurchaseRequestStatus.PENDING,
    PurchaseRequestStatus.APPROVED,
    PurchaseRequestStatus.ORDERED,
}


def json_safe(value: Any) -> Any:
    """Convert ORM-friendly Python values into JSON-serialisable values."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]
    return str(value)
