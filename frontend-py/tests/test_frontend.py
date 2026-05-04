import app as frontend_app
from app import create_app


def test_index_page_loads():
    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"Elemental Duel" in response.data


def test_index_renders_analytics_values(monkeypatch):
    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()

    monkeypatch.setattr(frontend_app, "ping_service", lambda _: "Online")
    monkeypatch.setattr(
        frontend_app,
        "get_analytics_summary",
        lambda _: {
            "total_rounds": 5,
            "wins": 3,
            "losses": 1,
            "draws": 1,
            "win_rate": 60,
            "source_status": "online",
            "notes": "ok",
            "generated_at": "now",
        },
    )

    response = client.get("/")

    assert response.status_code == 200
    assert b"Total rounds: 5" in response.data
    assert b"Wins: 3" in response.data


def test_play_flashes_result_message(monkeypatch):
    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()

    class MockResponse:
        @staticmethod
        def raise_for_status():
            return None

        @staticmethod
        def json():
            return {
                "round": {
                    "player_choice": "fire",
                    "computer_choice": "earth",
                    "result": "win",
                }
            }

    monkeypatch.setattr(frontend_app.requests, "post", lambda *args, **kwargs: MockResponse())
    monkeypatch.setattr(frontend_app, "ping_service", lambda _: "Online")
    monkeypatch.setattr(
        frontend_app,
        "get_analytics_summary",
        lambda _: {
            "total_rounds": 0,
            "wins": 0,
            "losses": 0,
            "draws": 0,
            "win_rate": 0,
            "source_status": "offline",
            "notes": "n/a",
            "generated_at": "n/a",
        },
    )

    response = client.post("/play", data={"element": "Fire"}, follow_redirects=True)

    assert response.status_code == 200
    assert b"Result: WIN" in response.data
