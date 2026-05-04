import os

import requests
from flask import Flask, flash, redirect, render_template, request, url_for

ELEMENTS = ["Fire", "Water", "Earth", "Air", "Lightning"]

ELEMENT_GRAPHICS = {
    "Fire": "🔥",
    "Water": "🌊",
    "Earth": "🪨",
    "Air": "🌪️",
    "Lightning": "⚡",
}


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
            "wins": 0,
            "losses": 0,
            "draws": 0,
            "win_rate": 0,
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
            {"name": "Frontend", "url": "http://localhost:5050", "status": "Online"},
            {"name": "Battle API", "url": battle_api_url, "status": ping_service(f"{battle_api_url}/health")},
            {"name": "Analytics API", "url": analytics_api_url, "status": ping_service(f"{analytics_api_url}/health")},
        ]

        player_choice = request.args.get("duel_player")
        opponent_choice = request.args.get("duel_opponent")
        duel_result = request.args.get("duel_result")
        duel_state = None

        if player_choice and opponent_choice and duel_result:
            player_label = player_choice.strip().title()
            opponent_label = opponent_choice.strip().title()
            result_key = duel_result.strip().lower()

            verdict_text = "Draw"
            verdict_class = "text-yellow-300"
            verdict_icon = "remove"
            if result_key == "win":
                verdict_text = "Victory"
                verdict_class = "text-emerald-300"
                verdict_icon = "military_tech"
            elif result_key == "lose":
                verdict_text = "Defeat"
                verdict_class = "text-rose-300"
                verdict_icon = "sentiment_dissatisfied"

            duel_state = {
                "player_choice": player_label,
                "opponent_choice": opponent_label,
                "player_emoji": ELEMENT_GRAPHICS.get(player_label, "✨"),
                "opponent_emoji": ELEMENT_GRAPHICS.get(opponent_label, "✨"),
                "result_key": result_key,
                "verdict_text": verdict_text,
                "verdict_class": verdict_class,
                "verdict_icon": verdict_icon,
            }

        analytics = get_analytics_summary(analytics_api_url)
        return render_template(
            "index.html",
            elements=ELEMENTS,
            element_graphics=ELEMENT_GRAPHICS,
            services=services,
            analytics=analytics,
            duel_state=duel_state,
        )

    @app.post("/play")
    def play():
        element = request.form.get("element", "Fire")
        payload = {"player_choice": element.lower()}

        try:
            response = requests.post(f"{battle_api_url}/api/v1/rounds", json=payload, timeout=5)
            response.raise_for_status()
            data = response.json()
            round_data = data.get("round", {})
            player_choice = round_data.get("player_choice", element.lower())
            opponent_choice = round_data.get("computer_choice", "unknown")
            duel_result = round_data.get("result", "draw")
            message = (
                f"You chose {player_choice}. "
                f"Computer chose {opponent_choice}. "
                f"Result: {duel_result.upper()}."
            )
            flash(message, "success")
            return redirect(
                url_for(
                    "index",
                    duel_player=player_choice,
                    duel_opponent=opponent_choice,
                    duel_result=duel_result,
                )
            )
        except requests.RequestException as exc:
            flash(f"Battle API unavailable: {exc}", "danger")

        return redirect(url_for("index"))

    return app

app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
