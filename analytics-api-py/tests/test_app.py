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
