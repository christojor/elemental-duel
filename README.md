# Elemental Duel

Elemental Duel is a cloud-native monorepo prepared for a microservices-based game platform.

## Services

- **Frontend**: Flask + Jinja2 + Bootstrap UI
- **Battle API**: Go + Gin + GORM + MySQL
- **Analytics API**: Python + Flask-RESTX + SQLite

## Local development

1. Copy environment values if needed:
   - `.env.example` contains a shareable template
   - `.env` is ready for local Docker Compose usage
2. Build and start everything:

```bash
docker compose up --build
```

## Endpoints

- Frontend: http://localhost:5050
- Battle API health: http://localhost:8088/health
- Analytics API docs: http://localhost:5002/docs

## Kubernetes

Apply the namespace first and then the service manifests:

```bash
kubectl apply -f k8s/namespace.yml
kubectl apply -f battle-api-go/k8s/battle.yml
kubectl apply -f analytics-api-py/k8s/analytics.yml
kubectl apply -f frontend-py/k8s/frontend.yml
```

## Game logic

Elemental Duel is implemented with five elements: `fire`, `water`, `earth`, `air`, `lightning`.

Each round resolves to `win`, `lose`, or `draw`, is persisted by the Battle API, and is aggregated by the Analytics API.

## Testing

This repository includes a full test pyramid:

- Unit tests for Go and Python services
- Integration tests for cross-service behavior (`tests/integration`)
- API contract tests via Postman/Newman (`tests/postman`)
- End-to-end browser tests via Playwright (`tests/e2e`)

## CI/CD

The GitHub Actions workflow performs selective monorepo checks for changed services, builds container images, and runs a full Docker Compose-based suite including integration, Newman, and Playwright tests.
