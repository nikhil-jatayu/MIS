from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator

from app.schemas.common import ORMModel
from app.schemas.user import UserSummary


class ProductionEntryCreate(ORMModel):
    production_date: date
    production_line: str = Field(min_length=1, max_length=120)
    product_model: str = Field(min_length=1, max_length=200)
    work_order_customer: str | None = Field(default=None, max_length=200)
    process_stage: str = Field(min_length=1, max_length=120)
    unit_of_measure: str = Field(min_length=1, max_length=30)
    planned_quantity: Decimal = Field(ge=0, max_digits=14, decimal_places=3)
    actual_quantity: Decimal = Field(ge=0, max_digits=14, decimal_places=3)
    accepted_quantity: Decimal = Field(ge=0, max_digits=14, decimal_places=3)
    rework_quantity: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=3)
    production_hours: Decimal = Field(default=Decimal("0"), ge=0, max_digits=10, decimal_places=2)
    downtime_hours: Decimal = Field(default=Decimal("0"), ge=0, max_digits=10, decimal_places=2)
    project_id: UUID | None = None
    remarks: str | None = Field(default=None, max_length=5000)

    @field_validator("production_line", "product_model", "process_stage")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank")
        return value

    @field_validator("unit_of_measure")
    @classmethod
    def normalize_unit(cls, value: str) -> str:
        value = value.strip().lower()
        if not value:
            raise ValueError("Unit of measure cannot be blank")
        return value

    @field_validator("work_order_customer", "remarks")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None

    @model_validator(mode="after")
    def validate_quantities(self):
        if self.accepted_quantity > self.actual_quantity:
            raise ValueError("Accepted quantity cannot exceed actual quantity")
        if self.rework_quantity > self.actual_quantity:
            raise ValueError("Rework quantity cannot exceed actual quantity")
        return self


class ProductionEntryUpdate(ORMModel):
    production_date: date | None = None
    production_line: str | None = Field(default=None, min_length=1, max_length=120)
    product_model: str | None = Field(default=None, min_length=1, max_length=200)
    work_order_customer: str | None = Field(default=None, max_length=200)
    process_stage: str | None = Field(default=None, min_length=1, max_length=120)
    unit_of_measure: str | None = Field(default=None, min_length=1, max_length=30)
    planned_quantity: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=3)
    actual_quantity: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=3)
    accepted_quantity: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=3)
    rework_quantity: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=3)
    production_hours: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    downtime_hours: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    project_id: UUID | None = None
    remarks: str | None = Field(default=None, max_length=5000)

    @field_validator("production_line", "product_model", "process_stage")
    @classmethod
    def strip_required_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank")
        return value

    @field_validator("unit_of_measure")
    @classmethod
    def normalize_unit(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().lower()
        if not value:
            raise ValueError("Unit of measure cannot be blank")
        return value

    @field_validator("work_order_customer", "remarks")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class ProductionEntryRead(ORMModel):
    id: UUID
    production_date: date
    production_line: str
    product_model: str
    work_order_customer: str | None
    process_stage: str
    unit_of_measure: str
    planned_quantity: float
    actual_quantity: float
    accepted_quantity: float
    rework_quantity: float
    production_hours: float
    downtime_hours: float
    project_id: UUID | None
    remarks: str | None
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    creator: UserSummary

    @computed_field
    @property
    def month(self) -> str:
        return self.production_date.strftime("%Y-%m")

    @computed_field
    @property
    def rejected_quantity(self) -> float:
        return max(self.actual_quantity - self.accepted_quantity, 0.0)

    @computed_field
    @property
    def plan_achievement_percent(self) -> float | None:
        if self.planned_quantity == 0:
            return None
        return (self.actual_quantity / self.planned_quantity) * 100.0

    @computed_field
    @property
    def first_pass_yield_percent(self) -> float | None:
        if self.actual_quantity == 0:
            return None
        return (self.accepted_quantity / self.actual_quantity) * 100.0

    @computed_field
    @property
    def rejection_percent(self) -> float | None:
        if self.actual_quantity == 0:
            return None
        return (self.rejected_quantity / self.actual_quantity) * 100.0

    @computed_field
    @property
    def downtime_percent(self) -> float | None:
        denominator = self.production_hours + self.downtime_hours
        if denominator == 0:
            return None
        return (self.downtime_hours / denominator) * 100.0


class ProductionActionCreate(ORMModel):
    date_raised: date = Field(default_factory=date.today)
    issue_observation: str = Field(min_length=3, max_length=5000)
    corrective_action: str = Field(min_length=3, max_length=5000)
    responsible_user_id: UUID
    deadline: date
    remarks: str | None = Field(default=None, max_length=5000)
    project_id: UUID | None = None
    production_entry_id: UUID | None = None

    @field_validator("issue_observation", "corrective_action")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank")
        return value


class ProductionActionUpdate(ORMModel):
    issue_observation: str | None = Field(default=None, min_length=3, max_length=5000)
    corrective_action: str | None = Field(default=None, min_length=3, max_length=5000)
    responsible_user_id: UUID | None = None
    deadline: date | None = None
    status: str | None = Field(default=None, pattern="^(OPEN|IN_PROGRESS|ON_HOLD|CLOSED)$")
    closure_evidence: str | None = Field(default=None, max_length=5000)
    remarks: str | None = Field(default=None, max_length=5000)

    @field_validator("issue_observation", "corrective_action")
    @classmethod
    def strip_required_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank")
        return value


class ProductionActionRead(ORMModel):
    id: UUID
    action_number: str
    date_raised: date
    issue_observation: str
    corrective_action: str
    responsible_user_id: UUID | None
    deadline: date
    status: str
    closed_at: datetime | None
    closed_by_user_id: UUID | None
    closure_evidence: str | None
    remarks: str | None
    project_id: UUID | None
    production_entry_id: UUID | None
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    responsible_user: UserSummary | None
    creator: UserSummary
    closed_by: UserSummary | None

    @computed_field
    @property
    def is_overdue(self) -> bool:
        return self.status != "CLOSED" and self.deadline < date.today()


class ProductionMonthlyReviewUpsert(ORMModel):
    management_summary: str = Field(min_length=3, max_length=10000)
    mark_reviewed: bool = False

    @field_validator("management_summary")
    @classmethod
    def strip_summary(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Management summary cannot be blank")
        return value


class ProductionMonthlyReviewRead(ORMModel):
    id: UUID
    year: int
    month: int
    management_summary: str
    prepared_by_user_id: UUID
    reviewed_by_user_id: UUID | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    prepared_by: UserSummary
    reviewed_by: UserSummary | None


class ProductionAssigneeRead(BaseModel):
    id: UUID
    name: str


class ProductionUnitSummary(BaseModel):
    unit_of_measure: str
    entries_count: int
    planned_quantity: float
    actual_quantity: float
    accepted_quantity: float
    rejected_quantity: float
    rework_quantity: float
    production_hours: float
    downtime_hours: float
    plan_achievement_percent: float | None
    first_pass_yield_percent: float | None
    rejection_percent: float | None
    downtime_percent: float | None


class ProductionSummaryRead(BaseModel):
    year: int
    month: int
    units: list[ProductionUnitSummary]
    open_actions: int
    overdue_actions: int
    closed_this_month: int
    monthly_review: ProductionMonthlyReviewRead | None


__all__ = [
    "ProductionActionCreate",
    "ProductionActionRead",
    "ProductionActionUpdate",
    "ProductionAssigneeRead",
    "ProductionEntryCreate",
    "ProductionEntryRead",
    "ProductionEntryUpdate",
    "ProductionMonthlyReviewRead",
    "ProductionMonthlyReviewUpsert",
    "ProductionSummaryRead",
]
