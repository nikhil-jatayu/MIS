#!/usr/bin/env python3
"""Populate a LOCAL MIS instance with repeatable, clearly labelled production demo data.

The script only uses MIS HTTP APIs. It never writes directly to PostgreSQL and it
never deletes or updates ordinary user records. Re-running it is idempotent for the
same marker/date range: existing demo records are detected and skipped.

Run from backend/ with its virtual environment activated:
    python scripts/seed_production_demo.py --dry-run
    python scripts/seed_production_demo.py --days 90
"""
from __future__ import annotations

import argparse
import getpass
import re
import sys
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from urllib.parse import urlparse

try:
    import httpx
except ImportError:  # pragma: no cover - environment-specific guidance
    print("Missing dependency 'httpx'. Activate backend/.venv and run: python -m pip install httpx")
    raise SystemExit(2)

API_PREFIX = "/api/v1"
DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_MARKER = "MIS-DEMO-REPORTING-V1"
PAGE_SIZE = 100

LINES = ["Assembly Line A", "Assembly Line B", "Finishing Line"]
PRODUCTS = [
    {"name": "Control Unit CU-100", "unit": "pcs", "stage": "Assembly"},
    {"name": "Power Module PM-220", "unit": "pcs", "stage": "Electrical Testing"},
    {"name": "Metal Enclosure ME-310", "unit": "pcs", "stage": "Fabrication"},
    {"name": "Protective Coating PC-450", "unit": "kg", "stage": "Coating"},
]
CUSTOMERS = ["North Plant", "West Components", "Delta Industrial", "Orion Systems"]
ACTION_TEMPLATES = [
    (
        "OPEN", -10, "Packaging label alignment inconsistent",
        "Verify label positioning and add a first-piece inspection.",
    ),
    (
        "OPEN", -3, "Assembly torque variation observed",
        "Recalibrate the torque tool and record verification results.",
    ),
    (
        "IN_PROGRESS", -6, "Intermittent test-station downtime",
        "Inspect test fixture connections and complete preventive maintenance.",
    ),
    (
        "IN_PROGRESS", 5, "Repeat rework on connector fitment",
        "Review the work instruction and retrain the affected operators.",
    ),
    (
        "ON_HOLD", 9, "Supplier coating sample awaiting approval",
        "Obtain the approved sample and document supplier confirmation.",
    ),
    (
        "CLOSED", -8, "Incorrect work-order label on batch",
        "Correct the label and add a dispatch-stage verification.",
    ),
    (
        "CLOSED", -15, "Preventive maintenance checklist incomplete",
        "Update the checklist and record the supervisor review.",
    ),
    (
        "OPEN", 7, "Minor material handling damage",
        "Review handling method and add protective separators.",
    ),
    (
        "IN_PROGRESS", 12, "Production cycle time above target",
        "Measure cycle time by station and remove the identified bottleneck.",
    ),
    (
        "OPEN", -1, "First-pass inspection documentation missing",
        "Complete the inspection record and brief the shift team.",
    ),
    (
        "ON_HOLD", -4, "Replacement fixture component pending",
        "Track the replacement component and verify fitment on receipt.",
    ),
    (
        "CLOSED", -2, "Rework segregation area not clearly marked",
        "Mark the rework area and brief operators on segregation.",
    ),
]


def q(value: Decimal, places: str = "0.001") -> Decimal:
    return value.quantize(Decimal(places), rounding=ROUND_HALF_UP)


def make_entry_payload(day: date, day_index: int, line_index: int, marker: str) -> tuple[str, dict]:
    key = f"P-{day:%Y%m%d}-{line_index + 1}"
    product = PRODUCTS[(day_index + line_index) % len(PRODUCTS)]
    line = LINES[line_index]

    planned = Decimal(88 + ((day_index * 7 + line_index * 13) % 63))
    achievement_factors = [
        Decimal("0.88"), Decimal("0.94"), Decimal("0.98"), Decimal("1.03"),
        Decimal("1.08"), Decimal("0.91"), Decimal("1.00"), Decimal("1.05"),
    ]
    actual = q(planned * achievement_factors[(day_index + line_index) % len(achievement_factors)])
    rework_rates = [
        Decimal("0.015"), Decimal("0.025"), Decimal("0.040"),
        Decimal("0.055"), Decimal("0.030"), Decimal("0.070"),
    ]
    other_non_acceptance_rates = [
        Decimal("0.000"), Decimal("0.005"), Decimal("0.010"), Decimal("0.015")
    ]
    rework_rate = rework_rates[(day_index * 2 + line_index) % len(rework_rates)]
    rework = q(actual * rework_rate)
    other_rate = other_non_acceptance_rates[
        (day_index + 2 * line_index) % len(other_non_acceptance_rates)
    ]
    other = q(actual * other_rate)
    accepted = max(q(actual - rework - other), Decimal("0"))

    # The kg product uses one decimal place; piece-count products use whole numbers.
    if product["unit"] == "kg":
        planned = q(planned / Decimal("1.7"), "0.1")
        actual = q(actual / Decimal("1.7"), "0.1")
        rework = min(q(rework / Decimal("1.7"), "0.1"), actual)
        other = min(q(other / Decimal("1.7"), "0.1"), max(actual - rework, Decimal("0")))
        accepted = max(q(actual - rework - other, "0.1"), Decimal("0"))
    else:
        planned = planned.quantize(Decimal("1"))
        actual = actual.quantize(Decimal("1"))
        rework = min(rework.quantize(Decimal("1")), actual)
        other = min(other.quantize(Decimal("1")), max(actual - rework, Decimal("0")))
        accepted = max((actual - rework - other).quantize(Decimal("1")), Decimal("0"))

    production_hours = q(
        Decimal("6.5") + Decimal((day_index + line_index) % 9) / Decimal("4"),
        "0.01",
    )
    downtime_hours = q(
        Decimal("0.15") + Decimal((day_index * 3 + line_index * 2) % 11) / Decimal("10"),
        "0.01",
    )
    work_order = f"{marker}-WO-{day:%y%m%d}-{line_index + 1}"
    customer = CUSTOMERS[(day_index + line_index) % len(CUSTOMERS)]

    payload = {
        "production_date": day.isoformat(),
        "production_line": line,
        "product_model": product["name"],
        "work_order_customer": f"{work_order} | {customer}",
        "process_stage": product["stage"],
        "unit_of_measure": product["unit"],
        "planned_quantity": float(planned),
        "actual_quantity": float(actual),
        "accepted_quantity": float(accepted),
        "rework_quantity": float(rework),
        "production_hours": float(production_hours),
        "downtime_hours": float(downtime_hours),
        "project_id": None,
        "remarks": (
            f"[{marker}] record={key} | Synthetic demo data for reporting tests; "
            "not an operational record."
        ),
    }
    return key, payload


def build_entries(days: int, marker: str, today: date) -> list[tuple[str, dict]]:
    start = today - timedelta(days=days - 1)
    result: list[tuple[str, dict]] = []
    sample_days = list(range(0, days, 3))
    if sample_days[-1] != days - 1 and (days - 1 - sample_days[-1]) > 1:
        sample_days.append(days - 1)
    for day_index, offset in enumerate(sample_days):
        production_day = start + timedelta(days=offset)
        for line_index in range(len(LINES)):
            result.append(make_entry_payload(production_day, day_index, line_index, marker))
    return result


def extract_key(text: str | None, kind: str) -> str | None:
    if not text:
        return None
    match = re.search(rf"\b{re.escape(kind)}=([A-Za-z0-9_-]+)", text)
    return match.group(1) if match else None


def api_error(response: httpx.Response) -> RuntimeError:
    try:
        detail = response.json()
    except ValueError:
        detail = response.text[:1200]
    message = (
        f"HTTP {response.status_code} for {response.request.method} "
        f"{response.request.url}\n{detail}"
    )
    return RuntimeError(message)


def request_json(client: httpx.Client, method: str, path: str, **kwargs):
    response = client.request(method, path, **kwargs)
    if response.status_code >= 400:
        raise api_error(response)
    if response.status_code == 204 or not response.content:
        return None
    return response.json()


def fetch_all(client: httpx.Client, path: str, params: dict | None = None) -> list[dict]:
    collected: list[dict] = []
    page = 1
    while True:
        query = {**(params or {}), "page": page, "page_size": PAGE_SIZE}
        data = request_json(client, "GET", path, params=query)
        items = data.get("items", [])
        collected.extend(items)
        pages = int(data.get("pages", 1))
        if page >= pages or not items:
            break
        page += 1
    return collected


def login(client: httpx.Client) -> dict:
    email = input("MIS login email: ").strip()
    password = getpass.getpass("MIS password (input hidden): ")
    if not email or not password:
        raise RuntimeError("Email and password are required.")
    auth = request_json(
        client,
        "POST",
        f"{API_PREFIX}/auth/login",
        json={"email": email, "password": password},
    )
    user = auth.get("user", {})
    if user.get("must_change_password"):
        raise RuntimeError(
            "This account must change its temporary password before it can create records. "
            "Sign in to the MIS website, change the password, then rerun this script."
        )
    token = auth.get("access_token")
    if not token:
        raise RuntimeError("Login succeeded but the API did not return an access token.")
    client.headers["Authorization"] = f"Bearer {token}"
    me = request_json(client, "GET", f"{API_PREFIX}/auth/me")
    return me


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Seed repeatable synthetic Production demo data into local MIS."
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Local MIS backend URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=90,
        help="Inclusive date window to populate (30-365; default: 90)",
    )
    parser.add_argument(
        "--marker",
        default=DEFAULT_MARKER,
        help="Unique marker used to identify this demo dataset",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the planned dataset without connecting or writing",
    )
    args = parser.parse_args()

    if not 30 <= args.days <= 365:
        parser.error("--days must be between 30 and 365")
    parsed = urlparse(args.base_url)
    if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1"}:
        parser.error("For safety, this script only writes to http://localhost or http://127.0.0.1.")
    if not re.fullmatch(r"[A-Za-z0-9_-]{4,40}", args.marker):
        parser.error("--marker must be 4-40 letters, numbers, underscores or hyphens")

    today = date.today()
    date_from = today - timedelta(days=args.days - 1)
    entry_specs = build_entries(args.days, args.marker, today)
    action_specs = ACTION_TEMPLATES
    print("\nMIS LOCAL DEMO DATA SEEDER")
    print("==========================")
    print(f"Backend:          {args.base_url.rstrip('/')}")
    print(f"Dataset marker:   {args.marker}")
    print(f"Reporting window: {date_from} through {today} ({args.days} days)")
    print(f"Production rows:  {len(entry_specs)}")
    print(f"Action rows:      {len(action_specs)}")
    print("All records will be labelled as synthetic demo data.")
    print(
        "No existing record will be deleted. Existing demo rows with the same "
        "marker are skipped.\n"
    )

    if args.dry_run:
        print("DRY RUN ONLY: no connection made and no data written.")
        return 0

    if input('To continue, type exactly "SEED DEMO DATA": ').strip() != "SEED DEMO DATA":
        print("Cancelled. No data was written.")
        return 0

    try:
        with httpx.Client(
            base_url=args.base_url.rstrip("/"),
            timeout=30.0,
            follow_redirects=True,
        ) as client:
            health = request_json(client, "GET", "/health")
            print(f"Backend health: OK {health if health is not None else ''}")
            user = login(client)
            actor_id = user["id"]
            print(f"Authenticated as: {user.get('name')} ({user.get('role')})")

            entry_params = {"date_from": date_from.isoformat(), "date_to": today.isoformat()}
            current_entries = fetch_all(client, f"{API_PREFIX}/production/entries", entry_params)
            existing_entries: dict[str, dict] = {}
            for item in current_entries:
                key = extract_key(item.get("remarks"), "record")
                if key and args.marker in (item.get("remarks") or ""):
                    existing_entries[key] = item

            entry_ids: list[str] = []
            entries_created = 0
            entries_skipped = 0
            for key, payload in entry_specs:
                if key in existing_entries:
                    entry_ids.append(existing_entries[key]["id"])
                    entries_skipped += 1
                    continue
                created = request_json(
                    client,
                    "POST",
                    f"{API_PREFIX}/production/entries",
                    json=payload,
                )
                entry_ids.append(created["id"])
                entries_created += 1

            current_actions = fetch_all(client, f"{API_PREFIX}/production/actions")
            existing_actions: dict[str, dict] = {}
            for item in current_actions:
                key = extract_key(item.get("issue_observation"), "action")
                if key and args.marker in (item.get("issue_observation") or ""):
                    existing_actions[key] = item

            actions_created = 0
            actions_skipped = 0
            actions_updated = 0
            for index, (desired_status, days_to_deadline, issue, correction) in enumerate(
                action_specs
            ):
                key = f"A-{index + 1:02d}"
                if key in existing_actions:
                    action = existing_actions[key]
                    actions_skipped += 1
                    # If an interrupted earlier run left a freshly created demo action OPEN,
                    # apply its intended demo status. Preserve any later manual status changes.
                    if action.get("status") == "OPEN" and desired_status != "OPEN":
                        patch = {"status": desired_status}
                        if desired_status == "CLOSED":
                            patch["closure_evidence"] = (
                                f"[{args.marker}] Synthetic closure evidence for testing."
                            )
                        request_json(
                            client,
                            "PATCH",
                            f"{API_PREFIX}/production/actions/{action['id']}",
                            json=patch,
                        )
                        actions_updated += 1
                    continue

                date_raised = today - timedelta(days=7 + (index * 5))
                deadline = today + timedelta(days=days_to_deadline)
                entry_id = entry_ids[(index * 7) % len(entry_ids)] if entry_ids else None
                payload = {
                    "date_raised": date_raised.isoformat(),
                    "issue_observation": f"[{args.marker}] action={key} | {issue}",
                    "corrective_action": correction,
                    "responsible_user_id": actor_id,
                    "deadline": deadline.isoformat(),
                    "remarks": f"[{args.marker}] Synthetic demo action; not an operational task.",
                    "project_id": None,
                    "production_entry_id": entry_id,
                }
                created = request_json(
                    client,
                    "POST",
                    f"{API_PREFIX}/production/actions",
                    json=payload,
                )
                actions_created += 1
                if desired_status != "OPEN":
                    patch = {"status": desired_status}
                    if desired_status == "CLOSED":
                        patch["closure_evidence"] = (
                            f"[{args.marker}] Synthetic closure evidence for testing."
                        )
                    request_json(
                        client,
                        "PATCH",
                        f"{API_PREFIX}/production/actions/{created['id']}",
                        json=patch,
                    )

            # Read the report back through the same API the dashboard consumes.
            report = request_json(
                client,
                "GET",
                f"{API_PREFIX}/production/reports/summary",
                params={"date_from": date_from.isoformat(), "date_to": today.isoformat()},
            )

            print("\nSEED RESULT")
            print("-----------")
            print(f"Production entries created: {entries_created}")
            print(f"Production entries skipped: {entries_skipped}")
            print(f"Actions created:             {actions_created}")
            print(f"Actions already present:     {actions_skipped}")
            print(f"Action statuses repaired:    {actions_updated}")
            print(f"Report granularity:          {report.get('granularity')}")
            print(f"Data quality warnings:       {report.get('inconsistent_quality_record_count')}")
            print("\nTotals by unit:")
            for metric in report.get("totals_by_unit", []):
                print(
                    (
                        "  {unit}: {count} entries | planned {planned} | actual {actual} | "
                        "first-pass accepted {accepted} | rework {rework} | "
                        "FPY {fpy}% | downtime {down}%"
                    ).format(
                        unit=metric.get("unit_of_measure"),
                        count=metric.get("entries_count"),
                        planned=metric.get("planned_quantity"),
                        actual=metric.get("actual_quantity"),
                        accepted=metric.get("accepted_first_pass_quantity"),
                        rework=metric.get("rework_sent_quantity"),
                        fpy=metric.get("first_pass_yield_percent"),
                        down=metric.get("downtime_percent"),
                    )
                )
            print("\nActions:")
            action_summary = report.get("actions", {})
            print(
                f"  Created in period: {action_summary.get('actions_created_in_period')}"
            )
            print(f"  Currently open:    {action_summary.get('current_open_actions')}")
            print(f"  Currently overdue: {action_summary.get('current_overdue_actions')}")
            print(f"  Closed in period:  {action_summary.get('closed_actions_in_period')}")
            print(
                "\nFinished. Open MIS and check Production Log, Action Tracker "
                "and Reports > Production."
            )
            print(
                "To test daily trend granularity, use a custom range "
                "of the most recent 30 days."
            )
            return 0
    except httpx.ConnectError:
        print(
            "Could not connect to MIS. Start the backend at http://localhost:8000 "
            "and try again.",
            file=sys.stderr,
        )
        return 1
    except (httpx.HTTPError, RuntimeError, KeyError, ValueError) as exc:
        print(f"\nSeeding stopped: {exc}", file=sys.stderr)
        print(
            "Any records created before the error remain labelled with your demo marker.",
            file=sys.stderr,
        )
        print(
            "You can safely rerun the script; existing demo rows are detected and skipped.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
