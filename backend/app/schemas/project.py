from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.models.enums import (
    Priority,
    ProjectMemberRole,
    ProjectStatus,
    ProjectType,
    TestResult,
)
from app.schemas.common import ORMModel
from app.schemas.inventory import InventoryItemRead
from app.schemas.user import UserSummary


class ProjectMemberInput(ORMModel):
    user_id: UUID
    role_in_project: ProjectMemberRole


class ProjectBOMInput(ORMModel):
    item_id: UUID
    quantity_required: int = Field(gt=0, le=1_000_000)


class ProjectCreate(ORMModel):
    name: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    type: ProjectType
    priority: Priority = Priority.MEDIUM
    start_date: date | None = None
    end_date: date | None = None
    members: list[ProjectMemberInput] = Field(min_length=1)
    bom: list[ProjectBOMInput] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: str | None) -> str | None:
        return value.strip() if value else None

    @model_validator(mode="after")
    def validate_project(self) -> "ProjectCreate":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("End date must be on or after the start date")
        user_ids = [member.user_id for member in self.members]
        if len(user_ids) != len(set(user_ids)):
            raise ValueError("A user can only be assigned once per project")
        item_ids = [line.item_id for line in self.bom]
        if len(item_ids) != len(set(item_ids)):
            raise ValueError("Each inventory item may only appear once in the BOM")
        return self


class ProjectUpdate(ORMModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    priority: Priority | None = None
    start_date: date | None = None
    end_date: date | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else value


class ProjectMembersUpdate(ORMModel):
    members: list[ProjectMemberInput] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_members(self) -> "ProjectMembersUpdate":
        ids = [member.user_id for member in self.members]
        if len(ids) != len(set(ids)):
            raise ValueError("A user can only be assigned once per project")
        return self


class ProjectBOMUpdate(ORMModel):
    lines: list[ProjectBOMInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_lines(self) -> "ProjectBOMUpdate":
        ids = [line.item_id for line in self.lines]
        if len(ids) != len(set(ids)):
            raise ValueError("Each inventory item may only appear once in the BOM")
        return self


class ProjectMemberRead(ORMModel):
    id: UUID
    user: UserSummary
    role_in_project: ProjectMemberRole


class ProjectBOMRead(ORMModel):
    id: UUID
    item: InventoryItemRead
    quantity_required: int
    quantity_allocated: int
    quantity_shortage: int


class ProjectRead(ORMModel):
    id: UUID
    name: str
    description: str | None
    type: ProjectType
    status: ProjectStatus
    priority: Priority
    start_date: date | None
    end_date: date | None
    created_by: UUID
    status_changed_at: datetime
    progress_percent: int
    delay_reason: str | None
    paused_from_status: ProjectStatus | None
    test_result: TestResult | None
    test_note: str | None
    tested_by: UUID | None
    tested_at: datetime | None
    created_at: datetime
    updated_at: datetime
    creator: UserSummary
    tester: UserSummary | None
    members: list[ProjectMemberRead]
    bom_lines: list[ProjectBOMRead]
    is_inventory_ready: bool
    shortage_count: int
    pending_days: int


class SubmitTestingRequest(ORMModel):
    tester_id: UUID


class TestResultRequest(ORMModel):
    result: TestResult
    note: str = Field(min_length=3, max_length=5000)


class CompleteProjectRequest(ORMModel):
    note: str | None = Field(default=None, max_length=5000)


class ProjectRef(ORMModel):
    id: UUID
    name: str
    status: ProjectStatus
    type: ProjectType
