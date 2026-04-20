import os

import requests
from flask import Flask, flash, redirect, render_template, request, url_for

ELEMENTS = ["Fire", "Water", "Earth", "Air", "Lightning"]


def ping_service(url):
    try:
        response = requests.get(url, timeout=2)
        response.raise_for_status()
        return "Online"
    except requests.RequestException:
        return "Offline"


def get_analytics_summary(analytics_api_url):
    try:
        response = requests.get(f"{analytics_api_url}/api/v1/analytics/summary", timeout=3)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return {
            "total_rounds": 0,
            "source_status": "offline",
            "notes": "Analytics API could not be reached.",
            "generated_at": "n/a",
        }


def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")

    battle_api_url = os.getenv("BATTLE_API_URL", "http://battle-api:8080")
    analytics_api_url = os.getenv("ANALYTICS_API_URL", "http://analytics-api:5001")

    @app.get("/")
    def index():
        services = [
            {"name": "Frontend", "url": "http://localhost:5000", "status": "Online"},
            {"name": "Battle API", "url": battle_api_url, "status": ping_service(f"{battle_api_url}/health")},
            {"name": "Analytics API", "url": analytics_api_url, "status": ping_service(f"{analytics_api_url}/health")},
        ]
        analytics = get_analytics_summary(analytics_api_url)
        return render_template("index.html", elements=ELEMENTS, services=services, analytics=analytics)

    @app.post("/play")
    def play():
        element = request.form.get("element", "Fire")
        payload = {"player_choice": element.lower(), "computer_choice": "placeholder-ai"}

        try:
            response = requests.post(f"{battle_api_url}/api/v1/rounds", json=payload, timeout=5)
            response.raise_for_status()
            data = response.json()
            flash(data.get("message", "Round saved successfully."), "success")
        except requests.RequestException as exc:
            flash(f"Battle API unavailable: {exc}", "danger")

        return redirect(url_for("index"))

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
