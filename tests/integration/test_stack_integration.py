import os

import requests

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5050")
BATTLE_URL = os.getenv("BATTLE_URL", "http://localhost:8088")
ANALYTICS_URL = os.getenv("ANALYTICS_URL", "http://localhost:5002")


def test_services_health_endpoints():
    assert requests.get(f"{BATTLE_URL}/health", timeout=5).status_code == 200
    assert requests.get(f"{ANALYTICS_URL}/health", timeout=5).status_code == 200
    assert requests.get(f"{FRONTEND_URL}/", timeout=5).status_code == 200


def test_round_flow_updates_stats():
    create_response = requests.post(
        f"{BATTLE_URL}/api/v1/rounds",
        json={"player_choice": "fire", "computer_choice": "air"},
        timeout=5,
    )
    assert create_response.status_code == 201
    assert create_response.json()["round"]["result"] == "win"

    stats_response = requests.get(f"{BATTLE_URL}/api/v1/stats", timeout=5)
    assert stats_response.status_code == 200
    stats_payload = stats_response.json()
    assert stats_payload["total_rounds"] >= 1
    assert "wins" in stats_payload

    analytics_response = requests.get(f"{ANALYTICS_URL}/api/v1/analytics/summary", timeout=5)
    assert analytics_response.status_code == 200
    analytics_payload = analytics_response.json()
    assert analytics_payload["total_rounds"] >= 1
    assert analytics_payload["wins"] >= 1
