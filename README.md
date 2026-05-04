# Elemental Duel

A cloud-native microservices game platform built for the Cloud Native Computing course (Inlämningsuppgift 2). Players choose one of five elements and duel against the computer. Every round is persisted, and game statistics are tracked through a dedicated analytics service.

---

## Architecture

```
┌─────────────┐      HTTP      ┌──────────────────┐      MySQL       ┌───────────┐
│  Frontend   │ ─────────────► │   Battle API      │ ───────────────► │  MySQL DB │
│  (Python)   │                │   (Go + Gin)      │                  │  (MySQL)  │
│  port 5000  │ ◄────────────  │   port 8080       │                  └───────────┘
└─────────────┘                └──────────────────┘
       │                                │ HTTP (stats)
       │ HTTP                           ▼
       │                       ┌──────────────────┐      SQLite      ┌───────────┐
       └─────────────────────► │  Analytics API    │ ───────────────► │  SQLite   │
                                │  (Python/Flask)   │                  │  /data/   │
                                │  port 5001        │                  └───────────┘
                                └──────────────────┘
```

| Service | Language / Framework | Database | Port |
|---|---|---|---|
| **Battle API** | Go 1.22 + Gin + GORM | MySQL 8.4 | 8080 |
| **Analytics API** | Python 3.12 + Flask-RESTX | SQLite | 5001 |
| **Frontend** | Python 3.12 + Flask + Jinja2 | — | 5000 |

---

## VG Requirements Coverage

| Requirement | Implementation |
|---|---|
| CI with compile, unit tests, container build & push | GitHub Actions (`.github/workflows/CI.yml`) — per-service jobs, pushes to both GHCR and Docker Hub |
| Go web service with database | Battle API (`battle-api-go/`) — Go + Gin + GORM + MySQL |
| Kubernetes deployment (manual `kubectl`) | All manifests in `*/k8s/` and `k8s/` |
| Additional CRUD API in the other language | Analytics API (`analytics-api-py/`) — Python + Flask-RESTX + SQLite, full CRUD |
| Browsable API documentation | Swagger UI at `http://localhost:5001/docs` |
| Frontend | Flask frontend consuming both APIs |
| Database backup → S3 | CronJobs in `battle-api-go/k8s/battle.yml` and `analytics-api-py/k8s/analytics.yml` — `aws s3 cp` to configurable S3 bucket |

---

## Game Logic

Five elements: **fire**, **water**, **earth**, **air**, **lightning**.

Each element beats two others and loses to two others. Every round resolves to `win`, `lose`, or `draw`, is persisted to MySQL by the Battle API, and can be aggregated into snapshots by the Analytics API.

---

## Running Locally

### Option A — Docker Compose (quickest)

**Prerequisites:** Docker Desktop

```bash
# From elemental-duel/
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:5050 |
| Battle API | http://localhost:8088 |
| Analytics API + Swagger | http://localhost:5002/docs |

Stop with `Ctrl+C`, clean up with `docker compose down -v`.

---

### Option B — Kubernetes (local cluster)

**Prerequisites:** Docker Desktop with Kubernetes enabled (or minikube/kind), `kubectl`

#### 1. Apply all manifests

```bash
cd elemental-duel

kubectl apply -f k8s/namespace.yml
kubectl apply -f battle-api-go/k8s/battle.yml
kubectl apply -f analytics-api-py/k8s/analytics.yml
kubectl apply -f frontend-py/k8s/frontend.yml
```

> The S3 backup CronJobs require the `aws-credentials` Secret. Skip this step if you do not need backups, or follow the instructions in `k8s/aws-credentials.example.yml`.

#### 2. Verify pods are running

```bash
kubectl get pods -n elemental-duel
```

Wait until all pods show `Running` / `Ready`. The Battle API pod waits for MySQL to accept connections before it becomes ready.

#### 3. Access the services

The frontend Service is `ClusterIP`, so use port-forward to reach it from your browser:

```bash
# Frontend
kubectl port-forward svc/frontend 5000:5000 -n elemental-duel

# Battle API (optional — for direct API access)
kubectl port-forward svc/battle-api 8080:8080 -n elemental-duel

# Analytics API + Swagger (optional)
kubectl port-forward svc/analytics-api 5001:5001 -n elemental-duel
```

Open http://localhost:5000 in your browser.

#### 4. Tear down

```bash
kubectl delete namespace elemental-duel
```

---

### Optional — S3 Backup CronJobs

The `battle-api-go/k8s/battle.yml` and `analytics-api-py/k8s/analytics.yml` manifests include CronJobs that back up the MySQL database and the SQLite database to an S3 bucket.

```bash
# Copy the template and fill in your AWS credentials
cp k8s/aws-credentials.example.yml k8s/aws-credentials.yml
# Edit k8s/aws-credentials.yml — set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET
kubectl apply -f k8s/aws-credentials.yml
```

`k8s/aws-credentials.yml` is gitignored. Never commit real credentials.

---

## API Reference

### Battle API (Go) — `http://localhost:8088`

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness check |
| `GET` | `/api/v1/rounds` | List all rounds |
| `POST` | `/api/v1/rounds` | Play a round — body: `{"player_choice": "fire"}` |
| `GET` | `/api/v1/stats` | Win/loss/draw totals |

Valid choices: `fire`, `water`, `earth`, `air`, `lightning`

### Analytics API (Python) — `http://localhost:5002` · Swagger at `/docs`

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/analytics/summary` | Fetch stats from Battle API and save a snapshot |
| `GET` | `/api/v1/analytics/snapshots` | List all saved snapshots |
| `POST` | `/api/v1/analytics/snapshots` | Create a snapshot manually |
| `GET` | `/api/v1/analytics/snapshots/{id}` | Get a single snapshot |
| `PUT` | `/api/v1/analytics/snapshots/{id}` | Full update of a snapshot |
| `PATCH` | `/api/v1/analytics/snapshots/{id}` | Partial update of a snapshot |
| `DELETE` | `/api/v1/analytics/snapshots/{id}` | Delete a snapshot |

---

## Testing

The repository contains a full test pyramid:

| Layer | Tool | Location |
|---|---|---|
| Go unit tests | `go test` | `battle-api-go/` |
| Python unit tests | `pytest` | `analytics-api-py/tests/`, `frontend-py/tests/` |
| Integration tests | `pytest` | `tests/integration/` |
| API contract tests | Newman (Postman) | `tests/postman/` |
| E2E browser tests | Playwright | `tests/e2e/` |

Run unit tests locally:

```bash
# Go
cd battle-api-go && go test ./...

# Python (activate venv first)
cd analytics-api-py && pytest
cd frontend-py && pytest
```

The full integration + E2E suite runs automatically in CI via Docker Compose.

---

## CI/CD

GitHub Actions workflow: `.github/workflows/CI.yml`

- **Monorepo path filtering** — only the changed service's job runs on each push
- **Per-service jobs:** lint → unit tests → build image → push to GHCR and Docker Hub
- **Integration job:** spins up the full Docker Compose stack, runs Newman and Playwright tests
- **Docker Hub tags:** `protodoc/elemental-duel:battle-latest`, `analytics-latest`, `frontend-latest`

Required repository secrets: `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`

---

## Repository Structure

```
elemental-duel/
├── battle-api-go/          # Go Battle API + Dockerfile + k8s manifests
├── analytics-api-py/       # Python Analytics API + Dockerfile + k8s manifests
├── frontend-py/            # Python Frontend + Dockerfile + k8s manifests
├── k8s/                    # Shared manifests (namespace, aws-credentials template)
├── k8s-aws/                # AWS EKS overlay (gp2 StorageClass, LoadBalancer service)
├── docker-compose.yaml     # Local full-stack compose file
└── .github/workflows/      # CI pipeline
```
