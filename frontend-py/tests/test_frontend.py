from app import create_app


def test_index_page_loads():
    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"Elemental Duel" in response.data
