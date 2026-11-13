from __future__ import annotations

import argparse
import sys
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.engine import make_url

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings  # noqa: E402
from app.models.alert import Alert  # noqa: E402
from app.models.audit import AuditLog  # noqa: E402
from app.models.enums import (  # noqa: E402
    AlertType,
    Department,
    Priority,
    ProjectStatus,
    ProjectType,
    PurchaseRequestStatus,
    TestResult,
    UserRole,
)
from app.models.inventory import InventoryItem  # noqa: E402
from app.models.production import ProductionAction, ProductionEntry  # noqa: E402
from app.models.progress import ProgressLog  # noqa: E402
from app.models.project import Project, ProjectBOM, ProjectMember  # noqa: E402
from app.models.purchase import PurchaseRequest  # noqa: E402
from app.models.user import User  # noqa: E402

MARKER = "MIS-DEMO-DATA-V2"
CONFIRMATION = "SEED MIS DEMO DATA"

ITEM_SPECS = [
    ("001", "Demo Control Unit PCB", 200),
    ("002", "Demo Power Module", 15),
    ("003", "Demo Metal Enclosure", 60),
    ("004", "Demo Protective Coating", 160),
    ("005", "Demo Quality Test Fixture", 140),
    ("006", "Demo Sensor Assembly", 100),
    ("007", "Demo R&D Inspection Fixture", 70),
    ("008", "Demo Cable Harness", 100),
]

PROJECT_SPECS = [
    {
        "key": "PROJECT-01",
        "name": "DEMO · Control Unit Assembly",
        "status": ProjectStatus.IN_PRODUCTION,
        "priority": Priority.HIGH,
        "type": ProjectType.PRODUCTION,
        "progress": 65,
        "item": "001",
        "required": 120,
        "allocated": 120,
        "days_old": 18,
        "days_to_due": 6,
        "department": Department.PRODUCTION,
    },
    {
        "key": "PROJECT-02",
        "name": "DEMO · Power Module Procurement",
        "status": ProjectStatus.PENDING_INVENTORY,
        "priority": Priority.CRITICAL,
        "type": ProjectType.PRODUCTION,
        "progress": 20,
        "item": "002",
        "required": 80,
        "allocated": 15,
        "days_old": 12,
        "days_to_due": 10,
        "department": Department.PRODUCTION,
    },
    {
        "key": "PROJECT-03",
        "name": "DEMO · Metal Enclosure Delivery",
        "status": ProjectStatus.AWAITING_DELIVERY,
        "priority": Priority.HIGH,
        "type": ProjectType.PRODUCTION,
        "progress": 35,
        "item": "003",
        "required": 70,
        "allocated": 60,
        "days_old": 20,
        "days_to_due": -2,
        "department": Department.PRODUCTION,
    },
    {
        "key": "PROJECT-04",
        "name": "DEMO · Protective Coating Batch",
        "status": ProjectStatus.IN_PRODUCTION,
        "priority": Priority.MEDIUM,
        "type": ProjectType.PRODUCTION,
        "progress": 48,
        "item": "004",
        "required": 120,
        "allocated": 120,
        "days_old": 9,
        "days_to_due": 8,
        "department": Department.PRODUCTION,
    },
    {
        "key": "PROJECT-05",
        "name": "DEMO · Controller Quality Testing",
        "status": ProjectStatus.IN_TESTING,
        "priority": Priority.HIGH,
        "type": ProjectType.PRODUCTION,
        "progress": 88,
        "item": "005",
        "required": 100,
        "allocated": 100,
        "days_old": 16,
        "days_to_due": 2,
        "department": Department.TESTING,
    },
    {
        "key": "PROJECT-06",
        "name": "DEMO · Completed Sensor Assembly",
        "status": ProjectStatus.COMPLETED,
        "priority": Priority.LOW,
        "type": ProjectType.PRODUCTION,
        "progress": 100,
        "item": "006",
        "required": 80,
        "allocated": 80,
        "days_old": 35,
        "days_to_due": 0,
        "department": Department.TESTING,
    },
    {
        "key": "PROJECT-07",
        "name": "DEMO · R&D Inspection Fixture",
        "status": ProjectStatus.READY_FOR_PRODUCTION,
        "priority": Priority.MEDIUM,
        "type": ProjectType.RND,
        "progress": 8,
        "item": "007",
        "required": 50,
        "allocated": 50,
        "days_old": 5,
        "days_to_due": 20,
        "department": Department.R_D,
    },
    {
        "key": "PROJECT-08",
        "name": "DEMO · Cable Harness Supply",
        "status": ProjectStatus.READY_FOR_PRODUCTION,
        "priority": Priority.MEDIUM,
        "type": ProjectType.PRODUCTION,
        "progress": 5,
        "item": "008",
        "required": 100,
        "allocated": 100,
        "days_old": 7,
        "days_to_due": 15,
        "department": Department.PRODUCTION,
    },
]


def _require_local_database() -> None:
    parsed = make_url(settings.database_url)
    if parsed.host not in {"localhost", "127.0.0.1", "::1"}:
        raise SystemExit(
            "Safety stop: this demo seeder only accepts a database hosted on localhost/127.0.0.1."
        )
    if not parsed.database:
        raise SystemExit("DATABASE_URL must include a database name.")


def _audit(
    db,
    *,
    actor_id,
    action: str,
    entity: str,
    entity_id,
    key: str,
) -> None:
    db.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            entity=entity,
            entity_id=str(entity_id),
            after={"seed_marker": MARKER, "seed_key": key, "synthetic": True},
        )
    )


def _item_for_key(db, key: str) -> InventoryItem:
    sku = f"MISDEMO-{key}"
    item = db.scalar(select(InventoryItem).where(InventoryItem.sku == sku))
    if item:
        return item
    spec = next(value for value in ITEM_SPECS if value[0] == key)
    item = InventoryItem(
        id=uuid4(),
        name=spec[1],
        sku=sku,
        quantity_available=spec[2],
    )
    db.add(item)
    db.flush()
    return item


def _project_for_key(db, key: str) -> Project | None:
    marker_text = f"[{MARKER}:{key}]"
    return db.scalar(select(Project).where(Project.description.contains(marker_text)))


def _create_projects(
    db, actor: User, items: dict[str, InventoryItem]
) -> tuple[dict[str, Project], int]:
    today = date.today()
    now = datetime.now(UTC)
    projects: dict[str, Project] = {}
    created = 0

    for spec in PROJECT_SPECS:
        key = spec["key"]
        existing = _project_for_key(db, key)
        if existing:
            projects[key] = existing
            continue

        item = items[spec["item"]]
        allocated = int(spec["allocated"])
        if item.quantity_available < allocated:
            raise RuntimeError(
                f"Demo inventory {item.sku} has {item.quantity_available} available, "
                f"but project {key} needs {allocated} allocated units."
            )
        item.quantity_available -= allocated

        project_id = uuid4()
        changed_at = now - timedelta(days=int(spec["days_old"]))
        project = Project(
            id=project_id,
            name=spec["name"],
            description=(
                "Synthetic sample project created for MIS dashboard and workflow testing. "
                f"[{MARKER}:{key}]"
            ),
            type=spec["type"],
            status=spec["status"],
            priority=spec["priority"],
            start_date=today - timedelta(days=int(spec["days_old"])),
            end_date=today + timedelta(days=int(spec["days_to_due"])),
            created_by=actor.id,
            status_changed_at=changed_at,
            progress_percent=int(spec["progress"]),
            delay_reason=(
                "Synthetic supplier delivery delay for workflow testing."
                if spec["status"] == ProjectStatus.AWAITING_DELIVERY
                else None
            ),
            paused_from_status=(
                ProjectStatus.IN_PRODUCTION
                if spec["status"] == ProjectStatus.AWAITING_DELIVERY
                else None
            ),
            test_result=(
                TestResult.PASS if spec["status"] == ProjectStatus.COMPLETED else None
            ),
            test_note=(
                "Synthetic QA sign-off record for demo data."
                if spec["status"] == ProjectStatus.COMPLETED
                else None
            ),
            tested_by=(actor.id if spec["status"] == ProjectStatus.COMPLETED else None),
            tested_at=(changed_at if spec["status"] == ProjectStatus.COMPLETED else None),
            assigned_tester_id=(
                actor.id
                if spec["status"] in {ProjectStatus.IN_TESTING, ProjectStatus.COMPLETED}
                else None
            ),
            created_at=changed_at,
            updated_at=changed_at,
        )
        db.add(project)
        db.flush()
        db.add(
            ProjectMember(
                id=uuid4(),
                project_id=project.id,
                user_id=actor.id,
                department=spec["department"],
                created_at=changed_at,
            )
        )
        db.add(
            ProjectBOM(
                id=uuid4(),
                project_id=project.id,
                item_id=item.id,
                quantity_required=int(spec["required"]),
                quantity_allocated=allocated,
            )
        )
        progress_value = min(int(spec["progress"]), 95)
        if progress_value > 0:
            db.add(
                ProgressLog(
                    id=uuid4(),
                    project_id=project.id,
                    user_id=actor.id,
                    note=f"{MARKER}:{key}: synthetic progress update",
                    progress_percent=progress_value,
                    created_at=changed_at + timedelta(days=1),
                )
            )
        projects[key] = project
        _audit(
            db,
            actor_id=actor.id,
            action="DEMO_SEED_CREATE",
            entity="project",
            entity_id=project.id,
            key=key,
        )
        created += 1

    return projects, created


def _create_purchase_requests(
    db,
    actor: User,
    projects: dict[str, Project],
    items: dict[str, InventoryItem],
) -> int:
    now = datetime.now(UTC)
    specs = [
        ("PR-01", "PROJECT-02", "002", 25, PurchaseRequestStatus.PENDING),
        ("PR-02", "PROJECT-02", "002", 20, PurchaseRequestStatus.APPROVED),
        ("PR-03", "PROJECT-02", "002", 10, PurchaseRequestStatus.REJECTED),
        ("PR-04", "PROJECT-03", "003", 10, PurchaseRequestStatus.ORDERED),
        ("PR-05", "PROJECT-03", "003", 20, PurchaseRequestStatus.DELIVERED),
    ]
    created = 0
    for key, project_key, item_key, quantity, status in specs:
        marker_text = f"[{MARKER}:{key}]"
        existing = db.scalar(
            select(PurchaseRequest).where(PurchaseRequest.reason.contains(marker_text))
        )
        if existing:
            continue
        project = projects[project_key]
        item = items[item_key]
        approved_at = now - timedelta(days=3) if status in {
            PurchaseRequestStatus.APPROVED,
            PurchaseRequestStatus.ORDERED,
            PurchaseRequestStatus.DELIVERED,
        } else None
        ordered_at = now - timedelta(days=2) if status in {
            PurchaseRequestStatus.ORDERED,
            PurchaseRequestStatus.DELIVERED,
        } else None
        delivered_at = (
            now - timedelta(days=1)
            if status == PurchaseRequestStatus.DELIVERED
            else None
        )
        request = PurchaseRequest(
            id=uuid4(),
            project_id=project.id,
            item_id=item.id,
            quantity=quantity,
            requested_by=actor.id,
            status=status,
            reason=f"Synthetic purchase workflow sample. {marker_text}",
            review_note=(
                "Synthetic rejection reason."
                if status == PurchaseRequestStatus.REJECTED
                else "Synthetic supplier delivery pending."
                if status == PurchaseRequestStatus.ORDERED
                else None
            ),
            approved_by=(actor.id if approved_at else None),
            approved_at=approved_at,
            ordered_at=ordered_at,
            delivered_at=delivered_at,
            created_at=now - timedelta(days=5),
            updated_at=now,
        )
        db.add(request)
        # Inventory and BOM allocation are seeded at their final post-delivery state.
        # This delivered request is part of the project's already-allocated BOM quantity.
        _audit(
            db,
            actor_id=actor.id,
            action="DEMO_SEED_CREATE",
            entity="purchase_request",
            entity_id=request.id,
            key=key,
        )
        created += 1
    return created


def _create_alerts(db, actor: User, projects: dict[str, Project]) -> int:
    today = date.today()
    specs = [
        ("ALERT-01", "PROJECT-02", AlertType.STANDARD, "Demo inventory shortage needs review."),
        ("ALERT-02", "PROJECT-03", AlertType.ESCALATED, "Demo supplier delivery is overdue."),
        ("ALERT-03", "PROJECT-01", AlertType.STANDARD, "Demo production milestone is approaching."),
    ]
    created = 0
    for key, project_key, alert_type, detail in specs:
        marker_text = f"[{MARKER}:{key}]"
        existing = db.scalar(select(Alert).where(Alert.message.contains(marker_text)))
        if existing:
            continue
        db.add(
            Alert(
                id=uuid4(),
                user_id=actor.id,
                project_id=projects[project_key].id,
                type=alert_type,
                message=f"{detail} {marker_text}",
                is_read=False,
                alert_date=today,
                created_at=datetime.now(UTC),
            )
        )
        created += 1
    return created


def _create_production_entries(
    db, actor: User, projects: dict[str, Project]
) -> tuple[int, list[ProductionEntry]]:
    today = date.today()
    now = datetime.now(UTC)
    project_keys = [spec["key"] for spec in PROJECT_SPECS]
    models = [
        ("Control Unit CU-100", "pcs", "Assembly"),
        ("Power Module PM-220", "pcs", "Testing"),
        ("Metal Enclosure ME-310", "pcs", "Fabrication"),
        ("Protective Coating PC-450", "kg", "Finishing"),
    ]
    created = 0
    entries: list[ProductionEntry] = []
    for index in range(20):
        key = f"PROD-{index + 1:02d}"
        marker_text = f"[{MARKER}:{key}]"
        existing = db.scalar(
            select(ProductionEntry).where(ProductionEntry.remarks.contains(marker_text))
        )
        if existing:
            entries.append(existing)
            continue
        product, unit, stage = models[index % len(models)]
        actual = Decimal(82 + ((index * 7) % 43))
        planned = actual + Decimal((index % 5) - 2) * Decimal("3")
        planned = max(planned, Decimal("1"))
        accepted = (actual * Decimal("0.965")).quantize(Decimal("0.001"))
        rework = (actual * Decimal("0.020")).quantize(Decimal("0.001"))
        entry_date = today - timedelta(days=(index * 2) % 28)
        project_key = project_keys[index % len(project_keys)]
        created_at = now - timedelta(days=(index * 2) % 28)
        entry = ProductionEntry(
            id=uuid4(),
            production_date=entry_date,
            production_line=(
                "Assembly Line A"
                if index % 3 == 0
                else "Assembly Line B"
                if index % 3 == 1
                else "Finishing Line"
            ),
            product_model=product,
            work_order_customer=f"DEMO-WO-{index + 1:03d}",
            process_stage=stage,
            unit_of_measure=unit,
            planned_quantity=planned,
            actual_quantity=actual,
            accepted_quantity=accepted,
            rework_quantity=rework,
            production_hours=Decimal("7.50"),
            downtime_hours=Decimal("0.50" if index % 4 == 0 else "0.15"),
            remarks=f"Synthetic production record {marker_text}",
            project_id=projects[project_key].id,
            created_by=actor.id,
            created_at=created_at,
            updated_at=created_at,
        )
        db.add(entry)
        db.flush()
        entries.append(entry)
        _audit(
            db,
            actor_id=actor.id,
            action="DEMO_SEED_CREATE",
            entity="production_entry",
            entity_id=entry.id,
            key=key,
        )
        created += 1
    return created, entries


def _create_production_actions(
    db,
    actor: User,
    projects: dict[str, Project],
    entries: list[ProductionEntry],
) -> int:
    today = date.today()
    now = datetime.now(UTC)
    specs = [
        ("ACTION-01", "PROJECT-01", 0, "OPEN", -3),
        ("ACTION-02", "PROJECT-02", 1, "IN_PROGRESS", 4),
        ("ACTION-03", "PROJECT-03", 2, "ON_HOLD", -1),
        ("ACTION-04", "PROJECT-04", 3, "CLOSED", -5),
        ("ACTION-05", "PROJECT-05", 4, "OPEN", 5),
        ("ACTION-06", "PROJECT-07", 6, "IN_PROGRESS", 2),
    ]
    created = 0
    for index, (key, project_key, entry_index, status, due_offset) in enumerate(specs):
        marker_text = f"[{MARKER}:{key}]"
        existing = db.scalar(
            select(ProductionAction).where(ProductionAction.remarks.contains(marker_text))
        )
        if existing:
            continue
        closed = status == "CLOSED"
        action_id = uuid4()
        action_number = f"MISDEMO-{key[-2:]}-{today:%y%m%d}"
        action = ProductionAction(
            id=action_id,
            action_number=action_number,
            date_raised=today - timedelta(days=5 + index),
            issue_observation=f"Synthetic production issue {index + 1}. {marker_text}",
            corrective_action=(
                "Inspect the affected batch, record findings and complete "
                "the corrective action."
            ),
            responsible_user_id=actor.id,
            deadline=today + timedelta(days=due_offset),
            status=status,
            closed_at=(now - timedelta(days=1) if closed else None),
            closed_by_user_id=(actor.id if closed else None),
            closure_evidence=("Synthetic verification evidence recorded." if closed else None),
            remarks=f"Synthetic action-tracker record {marker_text}",
            project_id=projects[project_key].id,
            production_entry_id=(entries[entry_index].id if entry_index < len(entries) else None),
            created_by=actor.id,
            created_at=now - timedelta(days=5 + index),
            updated_at=now,
        )
        db.add(action)
        _audit(
            db,
            actor_id=actor.id,
            action="DEMO_SEED_CREATE",
            entity="production_action",
            entity_id=action.id,
            key=key,
        )
        created += 1
    return created


def run_seed() -> dict[str, int]:
    _require_local_database()
    # Import the engine only when writing data so --dry-run remains connection-free.
    from app.db.session import SessionLocal

    with SessionLocal() as db:
        actor = db.scalar(
            select(User)
            .where(User.role == UserRole.SUPER_ADMIN, User.is_active.is_(True))
            .order_by(User.created_at.asc())
        )
        if not actor:
            raise RuntimeError(
                "No active Super Admin account exists. "
                "Create one before seeding demo data."
            )

        item_map = {key: _item_for_key(db, key) for key, _, _ in ITEM_SPECS}
        db.flush()
        project_map, projects_created = _create_projects(db, actor, item_map)
        purchases_created = _create_purchase_requests(db, actor, project_map, item_map)
        alerts_created = _create_alerts(db, actor, project_map)
        entries_created, entries = _create_production_entries(db, actor, project_map)
        actions_created = _create_production_actions(db, actor, project_map, entries)
        db.commit()

        return {
            "inventory_items_total": len(item_map),
            "projects_created": projects_created,
            "purchase_requests_created": purchases_created,
            "alerts_created": alerts_created,
            "production_entries_created": entries_created,
            "production_actions_created": actions_created,
        }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Add clearly marked, synthetic records to a local MIS database."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what the seeder is designed to create without connecting to the database.",
    )
    args = parser.parse_args()

    print("MIS local demo-data seeder")
    print(f"Marker: {MARKER}")
    print("Dataset: 8 inventory items, 8 projects, 5 purchase requests, 3 alerts,")
    print("         20 production entries, and 6 production actions.")
    print("The script never deletes records and skips rows it has already seeded.")

    if args.dry_run:
        print("DRY RUN ONLY: no database connection made and no data written.")
        return 0

    _require_local_database()
    print(f"Database host: {make_url(settings.database_url).host}")
    confirmation = input(f'Type "{CONFIRMATION}" to continue: ').strip()
    if confirmation != CONFIRMATION:
        print("Cancelled. No data was written.")
        return 1

    counts = run_seed()
    print("\nDemo seeding complete:")
    for label, value in counts.items():
        print(f"  {label}: {value}")
    print("\nAll seeded records are marked with MIS-DEMO-DATA-V2 for identification.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
