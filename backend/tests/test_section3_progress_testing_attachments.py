from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import settings
from tests.helpers import create_inventory_item, create_project


def _ready_project(client, auth_headers, standard_users, *, name="Flow Project", tester=False):
    item = create_inventory_item(
        client, auth_headers["super"], sku=f"FLOW-{name[:4].upper()}", quantity=20
    )
    members = [str(standard_users["user"].id)]
    if tester:
        members.append(str(standard_users["tester"].id))
    return create_project(
        client,
        auth_headers["admin"],
        name=name,
        member_ids=members,
        bom=[(item["id"], 2)],
    )


def test_progress_logs_are_append_only_and_restricted(
    client: TestClient, auth_headers, standard_users
):
    project = _ready_project(client, auth_headers, standard_users, name="Progress Build")

    first = client.post(
        f"/api/v1/projects/{project['id']}/progress-logs",
        headers=auth_headers["user"],
        json={"note": "Completed schematic capture", "progress_percent": 20},
    )
    assert first.status_code == 201, first.text
    assert first.json()["user"]["email"] == "member@jatayues.com"

    project_now = client.get(
        f"/api/v1/projects/{project['id']}", headers=auth_headers["user"]
    ).json()
    assert project_now["progress_percent"] == 20

    decrease = client.post(
        f"/api/v1/projects/{project['id']}/progress-logs",
        headers=auth_headers["user"],
        json={"note": "Rollback", "progress_percent": 10},
    )
    assert decrease.status_code == 422
    assert decrease.json()["error"]["code"] == "PROGRESS_DECREASE"

    full = client.post(
        f"/api/v1/projects/{project['id']}/progress-logs",
        headers=auth_headers["user"],
        json={"note": "Done", "progress_percent": 100},
    )
    assert full.status_code == 422
    assert full.json()["error"]["code"] == "PROGRESS_SIGN_OFF_REQUIRED"

    unassigned = client.post(
        f"/api/v1/projects/{project['id']}/progress-logs",
        headers=auth_headers["other"],
        json={"note": "Not my project", "progress_percent": 25},
    )
    assert unassigned.status_code == 403

    logs = client.get(
        f"/api/v1/projects/{project['id']}/progress-logs", headers=auth_headers["other"]
    )
    assert logs.status_code == 200
    assert logs.json()["total"] == 1

    log_id = first.json()["id"]
    edit = client.put(
        f"/api/v1/projects/{project['id']}/progress-logs/{log_id}",
        headers=auth_headers["admin"],
        json={"note": "tampered"},
    )
    assert edit.status_code in {404, 405}


def test_production_testing_pass_fail_and_signoff(client: TestClient, auth_headers, standard_users):
    project = _ready_project(
        client, auth_headers, standard_users, name="Testing Build", tester=True
    )
    assert project["status"] == "READY_FOR_PRODUCTION"

    user_start = client.post(
        f"/api/v1/projects/{project['id']}/start-production",
        headers=auth_headers["user"],
    )
    assert user_start.status_code == 403

    started = client.post(
        f"/api/v1/projects/{project['id']}/start-production",
        headers=auth_headers["admin"],
    )
    assert started.status_code == 200
    assert started.json()["status"] == "IN_PRODUCTION"

    not_member = client.post(
        f"/api/v1/projects/{project['id']}/submit-testing",
        headers=auth_headers["user"],
        json={"tester_id": str(standard_users["tester"].id)},
    )
    assert not_member.status_code == 403

    submitted = client.post(
        f"/api/v1/projects/{project['id']}/submit-testing",
        headers=auth_headers["admin"],
        json={"tester_id": str(standard_users["tester"].id)},
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "IN_TESTING"
    tester_membership = next(
        member
        for member in submitted.json()["members"]
        if member["user"]["id"] == str(standard_users["tester"].id)
    )
    assert tester_membership["role_in_project"] == "TESTER"

    wrong_tester = client.post(
        f"/api/v1/projects/{project['id']}/test-result",
        headers=auth_headers["user"],
        json={"result": "PASS", "note": "Looks good"},
    )
    assert wrong_tester.status_code == 403

    failed = client.post(
        f"/api/v1/projects/{project['id']}/test-result",
        headers=auth_headers["tester"],
        json={"result": "FAIL", "note": "Thermal test failed at 70 degrees"},
    )
    assert failed.status_code == 200, failed.text
    assert failed.json()["status"] == "IN_PRODUCTION"
    assert failed.json()["test_result"] == "FAIL"

    resubmitted = client.post(
        f"/api/v1/projects/{project['id']}/submit-testing",
        headers=auth_headers["admin"],
        json={"tester_id": str(standard_users["tester"].id)},
    )
    assert resubmitted.status_code == 200

    passed = client.post(
        f"/api/v1/projects/{project['id']}/test-result",
        headers=auth_headers["tester"],
        json={"result": "PASS", "note": "Re-test passed"},
    )
    assert passed.status_code == 200
    assert passed.json()["status"] == "IN_TESTING"
    assert passed.json()["test_result"] == "PASS"

    user_complete = client.post(
        f"/api/v1/projects/{project['id']}/complete",
        headers=auth_headers["user"],
        json={"note": "Done"},
    )
    assert user_complete.status_code == 403

    completed = client.post(
        f"/api/v1/projects/{project['id']}/complete",
        headers=auth_headers["admin"],
        json={"note": "QA passed and documentation archived"},
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "COMPLETED"
    assert completed.json()["progress_percent"] == 100

    after_complete = client.post(
        f"/api/v1/projects/{project['id']}/progress-logs",
        headers=auth_headers["user"],
        json={"note": "Late update", "progress_percent": 100},
    )
    assert after_complete.status_code == 409
    assert after_complete.json()["error"]["code"] == "PROJECT_COMPLETED"


def test_cannot_start_production_with_shortage(client: TestClient, auth_headers, standard_users):
    item = create_inventory_item(client, auth_headers["super"], sku="SHORT-001", quantity=0)
    project = create_project(
        client,
        auth_headers["admin"],
        name="Shortage Build",
        member_ids=[str(standard_users["user"].id)],
        bom=[(item["id"], 2)],
    )
    start = client.post(
        f"/api/v1/projects/{project['id']}/start-production",
        headers=auth_headers["admin"],
    )
    assert start.status_code == 409
    assert start.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"


def test_attachment_upload_download_and_limits(
    client: TestClient, auth_headers, standard_users, monkeypatch, tmp_path
):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))
    project = _ready_project(client, auth_headers, standard_users, name="Attachment Build")

    upload = client.post(
        f"/api/v1/projects/{project['id']}/attachments",
        headers=auth_headers["user"],
        files={"file": ("design-notes.txt", b"JES design notes", "text/plain")},
    )
    assert upload.status_code == 201, upload.text
    attachment = upload.json()
    assert attachment["filename"] == "design-notes.txt"
    assert attachment["size_bytes"] == len(b"JES design notes")
    assert attachment["uploader"]["email"] == "member@jatayues.com"
    assert attachment["download_url"].endswith("/download")

    listing = client.get(
        f"/api/v1/projects/{project['id']}/attachments", headers=auth_headers["user"]
    )
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    download = client.get(attachment["download_url"], headers=auth_headers["user"])
    assert download.status_code == 200
    assert download.content == b"JES design notes"

    denied = client.get(attachment["download_url"], headers=auth_headers["other"])
    assert denied.status_code == 403

    bad_type = client.post(
        f"/api/v1/projects/{project['id']}/attachments",
        headers=auth_headers["user"],
        files={"file": ("malware.exe", b"MZ", "application/octet-stream")},
    )
    assert bad_type.status_code == 415
    assert bad_type.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"

    monkeypatch.setattr(settings, "max_upload_size_mb", 0)
    too_large = client.post(
        f"/api/v1/projects/{project['id']}/attachments",
        headers=auth_headers["user"],
        files={"file": ("large.txt", b"too large", "text/plain")},
    )
    assert too_large.status_code == 413
    assert too_large.json()["error"]["code"] == "FILE_TOO_LARGE"
