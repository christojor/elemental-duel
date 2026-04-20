import os
from datetime import datetime
from pathlib import Path

import requests
from flask import Flask
from flask_restx import Api, Namespace, Resource
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class AnalyticsSnapshot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    total_rounds = db.Column(db.Integer, nullable=False, default=0)
    notes = db.Column(db.String(255), nullable=False, default="Scaffold mode")
    source_status = db.Column(db.String(32), nullable=False, default="unknown")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


def read_battle_stats():
    battle_api_url = os.getenv("BATTLE_API_URL", "http://battle-api:8080")
    stats_url = f"{battle_api_url}/api/v1/stats"

    try:
        response = requests.get(stats_url, timeout=3)
        response.raise_for_status()
        payload = response.json()
        return payload.get("total_rounds", 0), "online"
    except requests.RequestException:
        return 0, "offline"


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)

    config = test_config or {}
    database_uri = config.get("DATABASE_URI")

    if not database_uri:
        default_db_path = Path(os.getenv("ANALYTICS_DB_PATH", app.instance_path))
        if default_db_path.suffix != ".db":
            default_db_path = default_db_path / "analytics.db"
        default_db_path.parent.mkdir(parents=True, exist_ok=True)
        database_uri = f"sqlite:///{default_db_path}"

    app.config.update(
        TESTING=config.get("TESTING", False),
        SQLALCHEMY_DATABASE_URI=database_uri,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    db.init_app(app)

    api = Api(
        app,
        version="1.0",
        title="Elemental Duel Analytics API",
        description="Read-heavy analytics service with Swagger documentation.",
        doc="/docs",
    )

    analytics_ns = Namespace("analytics", description="Analytics operations")

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "analytics-api-py"}, 200

    @analytics_ns.route("/summary")
    class AnalyticsSummary(Resource):
        def get(self):
            total_rounds, source_status = read_battle_stats()
            latest = AnalyticsSnapshot.query.order_by(AnalyticsSnapshot.created_at.desc()).first()

            if latest is None:
                latest = AnalyticsSnapshot(
                    total_rounds=total_rounds,
                    source_status=source_status,
                    notes="Initial analytics scaffold record.",
                )
                db.session.add(latest)
                db.session.commit()

            return {
                "service": "analytics-api-py",
                "total_rounds": total_rounds,
                "source_status": source_status,
                "notes": latest.notes,
                "generated_at": latest.created_at.isoformat(),
            }, 200

    api.add_namespace(analytics_ns, path="/api/v1/analytics")

    with app.app_context():
        db.create_all()

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5001"))
    app.run(host="0.0.0.0", port=port)
