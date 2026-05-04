import os
from datetime import datetime
from pathlib import Path

import requests
from flask import Flask
from flask_restx import Api, Namespace, Resource
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect

db = SQLAlchemy()


class AnalyticsSnapshot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    total_rounds = db.Column(db.Integer, nullable=False, default=0)
    total_wins = db.Column(db.Integer, nullable=False, default=0)
    total_losses = db.Column(db.Integer, nullable=False, default=0)
    total_draws = db.Column(db.Integer, nullable=False, default=0)
    win_rate = db.Column(db.Float, nullable=False, default=0)
    notes = db.Column(db.String(255), nullable=False, default="Live battle statistics")
    source_status = db.Column(db.String(32), nullable=False, default="unknown")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


def snapshot_to_dict(snapshot):
    return {
        "id": snapshot.id,
        "total_rounds": snapshot.total_rounds,
        "wins": snapshot.total_wins,
        "losses": snapshot.total_losses,
        "draws": snapshot.total_draws,
        "win_rate": snapshot.win_rate,
        "source_status": snapshot.source_status,
        "notes": snapshot.notes,
        "generated_at": snapshot.created_at.isoformat(),
    }


def _coerce_int(value, field_name):
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be an integer")


def _coerce_float(value, field_name):
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be a number")


def parse_snapshot_payload(payload, partial=False):
    payload = payload or {}
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")

    field_map = {
        "total_rounds": ("total_rounds", _coerce_int),
        "wins": ("total_wins", _coerce_int),
        "losses": ("total_losses", _coerce_int),
        "draws": ("total_draws", _coerce_int),
        "win_rate": ("win_rate", _coerce_float),
        "source_status": ("source_status", str),
        "notes": ("notes", str),
    }

    unknown_keys = [key for key in payload.keys() if key not in field_map]
    if unknown_keys:
        unknown = ", ".join(sorted(unknown_keys))
        raise ValueError(f"unknown fields: {unknown}")

    required_keys = ["total_rounds", "wins", "losses", "draws", "win_rate"]
    if not partial:
        missing_keys = [key for key in required_keys if key not in payload]
        if missing_keys:
            missing = ", ".join(missing_keys)
            raise ValueError(f"missing required fields: {missing}")

    updates = {}
    for key, value in payload.items():
        model_field, converter = field_map[key]
        if converter is str:
            updates[model_field] = str(value)
        elif converter in (_coerce_int, _coerce_float):
            updates[model_field] = converter(value, key)
        else:
            updates[model_field] = value

    return updates


def read_battle_stats():
    battle_api_url = os.getenv("BATTLE_API_URL", "http://battle-api:8080")
    stats_url = f"{battle_api_url}/api/v1/stats"

    try:
        response = requests.get(stats_url, timeout=3)
        response.raise_for_status()
        payload = response.json()
        return {
            "total_rounds": payload.get("total_rounds", 0),
            "wins": payload.get("wins", 0),
            "losses": payload.get("losses", 0),
            "draws": payload.get("draws", 0),
            "win_rate": payload.get("win_rate", 0),
            "source_status": "online",
        }
    except requests.RequestException:
        return {
            "total_rounds": 0,
            "wins": 0,
            "losses": 0,
            "draws": 0,
            "win_rate": 0,
            "source_status": "offline",
        }


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
            stats = read_battle_stats()

            snapshot = AnalyticsSnapshot(
                total_rounds=stats["total_rounds"],
                total_wins=stats["wins"],
                total_losses=stats["losses"],
                total_draws=stats["draws"],
                win_rate=stats["win_rate"],
                source_status=stats["source_status"],
                notes="Snapshot from battle-api-go stats endpoint.",
            )
            db.session.add(snapshot)
            db.session.commit()

            return {"service": "analytics-api-py", **snapshot_to_dict(snapshot)}, 200

    @analytics_ns.route("/snapshots")
    class AnalyticsSnapshotCollection(Resource):
        def get(self):
            snapshots = AnalyticsSnapshot.query.order_by(AnalyticsSnapshot.id.desc()).all()
            return {
                "service": "analytics-api-py",
                "items": [snapshot_to_dict(snapshot) for snapshot in snapshots],
            }, 200

        def post(self):
            try:
                updates = parse_snapshot_payload(api.payload, partial=False)
            except ValueError as exc:
                return {"error": str(exc)}, 400

            snapshot = AnalyticsSnapshot(**updates)
            db.session.add(snapshot)
            db.session.commit()

            return {
                "service": "analytics-api-py",
                "message": "Snapshot created.",
                "snapshot": snapshot_to_dict(snapshot),
            }, 201

    @analytics_ns.route("/snapshots/<int:snapshot_id>")
    class AnalyticsSnapshotItem(Resource):
        def get(self, snapshot_id):
            snapshot = db.session.get(AnalyticsSnapshot, snapshot_id)
            if snapshot is None:
                return {"error": "snapshot not found"}, 404

            return {"service": "analytics-api-py", "snapshot": snapshot_to_dict(snapshot)}, 200

        def put(self, snapshot_id):
            snapshot = db.session.get(AnalyticsSnapshot, snapshot_id)
            if snapshot is None:
                return {"error": "snapshot not found"}, 404

            try:
                updates = parse_snapshot_payload(api.payload, partial=False)
            except ValueError as exc:
                return {"error": str(exc)}, 400

            for key, value in updates.items():
                setattr(snapshot, key, value)
            db.session.commit()

            return {
                "service": "analytics-api-py",
                "message": "Snapshot updated.",
                "snapshot": snapshot_to_dict(snapshot),
            }, 200

        def patch(self, snapshot_id):
            snapshot = db.session.get(AnalyticsSnapshot, snapshot_id)
            if snapshot is None:
                return {"error": "snapshot not found"}, 404

            try:
                updates = parse_snapshot_payload(api.payload, partial=True)
            except ValueError as exc:
                return {"error": str(exc)}, 400

            if not updates:
                return {"error": "no fields provided"}, 400

            for key, value in updates.items():
                setattr(snapshot, key, value)
            db.session.commit()

            return {
                "service": "analytics-api-py",
                "message": "Snapshot patched.",
                "snapshot": snapshot_to_dict(snapshot),
            }, 200

        def delete(self, snapshot_id):
            snapshot = db.session.get(AnalyticsSnapshot, snapshot_id)
            if snapshot is None:
                return {"error": "snapshot not found"}, 404

            db.session.delete(snapshot)
            db.session.commit()
            return {"service": "analytics-api-py", "message": "Snapshot deleted."}, 200

    api.add_namespace(analytics_ns, path="/api/v1/analytics")

    with app.app_context():
        expected_columns = {
            "id",
            "total_rounds",
            "total_wins",
            "total_losses",
            "total_draws",
            "win_rate",
            "notes",
            "source_status",
            "created_at",
        }
        inspector = inspect(db.engine)
        if inspector.has_table("analytics_snapshot"):
            existing_columns = {column["name"] for column in inspector.get_columns("analytics_snapshot")}
            if not expected_columns.issubset(existing_columns):
                db.drop_all()
        db.create_all()

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5001"))
    app.run(host="0.0.0.0", port=port)
