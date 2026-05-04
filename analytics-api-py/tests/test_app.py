import app as analytics_app
from app import create_app


def test_health_endpoint(tmp_path):
    db_file = tmp_path / "analytics-test.db"
    app = create_app({"TESTING": True, "DATABASE_URI": f"sqlite:///{db_file}"})
    client = app.test_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_swagger_docs_endpoint(tmp_path):
    db_file = tmp_path / "analytics-docs.db"
    app = create_app({"TESTING": True, "DATABASE_URI": f"sqlite:///{db_file}"})
    client = app.test_client()

    response = client.get("/docs")

    assert response.status_code == 200


def test_summary_returns_battle_stats(tmp_path, monkeypatch):
    db_file = tmp_path / "analytics-summary.db"
    app = create_app({"TESTING": True, "DATABASE_URI": f"sqlite:///{db_file}"})
    client = app.test_client()

    def mock_read_battle_stats():
        return {
            "total_rounds": 3,
            "wins": 2,
            "losses": 1,
            "draws": 0,
            "win_rate": 66.67,
            "source_status": "online",
        }

    monkeypatch.setattr(analytics_app, "read_battle_stats", mock_read_battle_stats)

    response = client.get("/api/v1/analytics/summary")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["total_rounds"] == 3
    assert payload["wins"] == 2
    assert payload["losses"] == 1
    assert payload["draws"] == 0
    assert payload["source_status"] == "online"


def test_summary_handles_offline_battle_api(tmp_path, monkeypatch):
    db_file = tmp_path / "analytics-offline.db"
    app = create_app({"TESTING": True, "DATABASE_URI": f"sqlite:///{db_file}"})
    client = app.test_client()

    monkeypatch.setattr(
        analytics_app,
        "read_battle_stats",
        lambda: {
            "total_rounds": 0,
            "wins": 0,
            "losses": 0,
            "draws": 0,
            "win_rate": 0,
            "source_status": "offline",
        },
    )

    response = client.get("/api/v1/analytics/summary")

    assert response.status_code == 200
    assert response.get_json()["source_status"] == "offline"


def test_snapshots_crud_lifecycle(tmp_path):
    db_file = tmp_path / "analytics-crud.db"
    app = create_app({"TESTING": True, "DATABASE_URI": f"sqlite:///{db_file}"})
    client = app.test_client()

    create_payload = {
        "total_rounds": 10,
        "wins": 6,
        "losses": 3,
        "draws": 1,
        "win_rate": 60.0,
        "source_status": "manual",
        "notes": "created from test",
    }

    create_response = client.post("/api/v1/analytics/snapshots", json=create_payload)
    assert create_response.status_code == 201
    created = create_response.get_json()["snapshot"]
    snapshot_id = created["id"]
    assert created["wins"] == 6

    list_response = client.get("/api/v1/analytics/snapshots")
    assert list_response.status_code == 200
    assert any(item["id"] == snapshot_id for item in list_response.get_json()["items"])

    get_response = client.get(f"/api/v1/analytics/snapshots/{snapshot_id}")
    assert get_response.status_code == 200
    assert get_response.get_json()["snapshot"]["notes"] == "created from test"

    update_payload = {
        "total_rounds": 20,
        "wins": 11,
        "losses": 7,
        "draws": 2,
        "win_rate": 55.0,
        "source_status": "manual",
        "notes": "updated with put",
    }
    put_response = client.put(f"/api/v1/analytics/snapshots/{snapshot_id}", json=update_payload)
    assert put_response.status_code == 200
    assert put_response.get_json()["snapshot"]["wins"] == 11

    patch_response = client.patch(
        f"/api/v1/analytics/snapshots/{snapshot_id}",
        json={"notes": "patched", "win_rate": 57.5},
    )
    assert patch_response.status_code == 200
    patched = patch_response.get_json()["snapshot"]
    assert patched["notes"] == "patched"
    assert patched["win_rate"] == 57.5

    delete_response = client.delete(f"/api/v1/analytics/snapshots/{snapshot_id}")
    assert delete_response.status_code == 200

    not_found_response = client.get(f"/api/v1/analytics/snapshots/{snapshot_id}")
    assert not_found_response.status_code == 404


def test_snapshots_validate_payload(tmp_path):
    db_file = tmp_path / "analytics-validation.db"
    app = create_app({"TESTING": True, "DATABASE_URI": f"sqlite:///{db_file}"})
    client = app.test_client()

    invalid_type_response = client.post(
        "/api/v1/analytics/snapshots",
        json={
            "total_rounds": "oops",
            "wins": 1,
            "losses": 0,
            "draws": 0,
            "win_rate": 100,
        },
    )
    assert invalid_type_response.status_code == 400

    missing_required_response = client.post(
        "/api/v1/analytics/snapshots",
        json={"wins": 1},
    )
    assert missing_required_response.status_code == 400

    unknown_field_response = client.post(
        "/api/v1/analytics/snapshots",
        json={
            "total_rounds": 1,
            "wins": 1,
            "losses": 0,
            "draws": 0,
            "win_rate": 100,
            "bonus": 42,
        },
    )
    assert unknown_field_response.status_code == 400
