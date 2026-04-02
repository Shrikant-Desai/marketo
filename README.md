# Marketo

A production-grade e-commerce backend API built with **FastAPI**. Supports full user management, product listings with full-text search, multi-item orders with stock control, Redis caching, background email tasks via **Celery**, and comprehensive structured logging.

## Features

- **JWT Authentication** — Register/login with access + refresh tokens; email-or-username login
- **Role-Based Access Control** — `user`, `seller`, `admin` roles; all endpoints protected by default
- **Product Management** — CRUD + PostgreSQL full-text search; Redis-cached reads; soft deletes
- **Multi-Item Orders** — Place orders with multiple products; server-side pricing; stock reservation; cancel with stock restore
- **Background Tasks** — Celery workers for welcome emails & order confirmations
- **Redis Caching** — Per-item and list caching with pattern-based invalidation
- **Structured Logging** — structlog throughout (JSON in production, pretty in dev)
- **Rate Limiting** — Sliding-window rate limiter via Redis (60 req/min default)
- **Health Probes** — `/health` (liveness) and `/health/ready` (readiness — checks DB + Redis)
- **Prometheus Metrics** — Auto-instrumented via `prometheus-fastapi-instrumentator`; custom counters in `core/metrics.py`
- **Docker-Ready** — Multi-stage Dockerfile + Docker Compose (API, Celery worker, Postgres, Redis)

## Technology Stack

| Layer            | Technology                           |
| ---------------- | ------------------------------------ |
| Framework        | FastAPI + Uvicorn / Gunicorn         |
| Database         | PostgreSQL + SQLAlchemy (async)      |
| Migrations       | Alembic                              |
| Caching / Broker | Redis                                |
| Task Worker      | Celery                               |
| Auth             | python-jose (JWT) + passlib (bcrypt) |
| Logging          | structlog                            |
| Validation       | Pydantic v2 + bleach                 |
| Containerization | Docker + Docker Compose              |

## Architecture

```
marketo/
├── auth/               # ← Canonical: JWT security + auth dependencies
│   ├── security.py     #   hash_password, create_access_token, decode_token
│   └── dependencies.py #   get_db, get_current_user, require_admin, require_roles
├── core/               # Config, exceptions, logging, metrics, (security/deps forward to auth/)
├── models/             # SQLAlchemy ORM: User, Product, Order, OrderItem
├── repositories/       # DB access layer (one class per model)
├── services/           # Business logic (user.py, product_service.py, order_service.py)
├── routers/            # FastAPI routers (user.py, products.py, orders.py, health.py)
├── schemas/            # Pydantic schemas (user.py is canonical; product.py, order.py)
├── middleware/         # LoggingMiddleware, RateLimitMiddleware, RequestTimingMiddleware
├── cache/              # Redis helpers (get_cache, set_cache, delete_pattern)
├── tasks/              # Celery: welcome email, order confirmation, vendor webhook
└── tests/              # pytest-asyncio: conftest, factory_boy factories
```

### Auth & Security Design

- **`auth/` is the canonical source** for all security utilities and FastAPI dependencies.
- `core/security.py` and `core/dependencies.py` are thin re-exports for backward compatibility.
- All **non-public endpoints require a Bearer token** (`Authorization: Bearer <token>`).
- **Public endpoints** (no auth required): `POST /v1/auth/register`, `POST /v1/auth/login`, `GET /health`, `GET /health/ready`, `GET /metrics`.

## Quick Start

### Option A — Docker (Recommended)

```bash
# 1. Copy and configure environment
cp .env .env.local  # edit JWT_SECRET_KEY + SMTP settings

# 2. Start everything
docker-compose up --build -d

# 3. Run migrations inside the API container
docker exec -it marketo-api alembic upgrade head

# 4. Browse the interactive docs
open http://localhost:8000/docs
```

### Option B — Local Development

**Prerequisites:** Python 3.12+, PostgreSQL, Redis

```bash
# 1. Create virtual environment
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/macOS

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
#    Edit .env — set JWT_SECRET_KEY and DATABASE_URL at minimum

# 4. Apply migrations
alembic upgrade head

# 5. Start the API server
uvicorn main:app --reload

# 6. (Optional) Start Celery worker in a second terminal
celery -A tasks.celery_app.celery_app worker --loglevel=info
```

## Environment Variables

| Variable                      | Required | Default                    | Description                                         |
| ----------------------------- | -------- | -------------------------- | --------------------------------------------------- |
| `JWT_SECRET_KEY`              | ✅       | —                          | Secret for JWT signing. Use `secrets.token_hex(32)` |
| `DATABASE_URL`                | ✅       | —                          | `postgresql+asyncpg://user:pass@host/db`            |
| `REDIS_URL`                   |          | `redis://localhost:6379/0` | Redis connection URL                                |
| `ENVIRONMENT`                 |          | `development`              | `development` \| `staging` \| `production`          |
| `DEBUG`                       |          | `false`                    | Enables SQL query logging + pretty logs             |
| `ACCESS_TOKEN_EXPIRE_MINUTES` |          | `30`                       | JWT access token lifetime                           |
| `REFRESH_TOKEN_EXPIRE_DAYS`   |          | `7`                        | JWT refresh token lifetime                          |
| `SMTP_*`                      |          | —                          | SMTP settings for email tasks (optional in dev)     |
| `ENABLE_METRICS`              |          | `true`                     | Expose `/metrics` Prometheus endpoint               |

## API Endpoints

### Public (no auth required)

| Method | Path                | Description                         |
| ------ | ------------------- | ----------------------------------- |
| `POST` | `/v1/auth/register` | Register a new account              |
| `POST` | `/v1/auth/login`    | Get access + refresh tokens         |
| `GET`  | `/health`           | Liveness probe                      |
| `GET`  | `/health/ready`     | Readiness probe (checks DB + Redis) |
| `GET`  | `/metrics`          | Prometheus metrics                  |

### Protected (Bearer token required)

| Method   | Path                        | Description                           |
| -------- | --------------------------- | ------------------------------------- |
| `GET`    | `/v1/users/me`              | Get current user profile              |
| `PUT`    | `/v1/users/me`              | Update current user profile           |
| `DELETE` | `/v1/users/me`              | Delete current user account           |
| `GET`    | `/v1/users/`                | List all users **(admin only)**       |
| `GET`    | `/v1/products/`             | List products (cached)                |
| `GET`    | `/v1/products/search?q=...` | Full-text product search              |
| `GET`    | `/v1/products/{id}`         | Get product by ID (cached)            |
| `POST`   | `/v1/products/`             | Create a product                      |
| `PUT`    | `/v1/products/{id}`         | Update a product                      |
| `DELETE` | `/v1/products/{id}`         | Soft-delete a product (owner only)    |
| `POST`   | `/v1/orders/`               | Place a new order                     |
| `GET`    | `/v1/orders/my`             | List my orders                        |
| `GET`    | `/v1/orders/{id}`           | Get order (owner only)                |
| `POST`   | `/v1/orders/{id}/cancel`    | Cancel pending order (restores stock)   |
| `PUT`    | `/v1/users/{id}/role`       | Change a user's role **(admin only)**   |

## Useful Docker Commands

```bash
# View logs
docker logs marketo-api -f
docker logs marketo-worker -f

# Run migrations
docker exec -it marketo-api alembic upgrade head

# Generate a new migration
docker exec -it marketo-api alembic revision --autogenerate -m "add field"

# Stop all containers
docker-compose stop

# Remove containers (keep data volumes)
docker-compose down

# Remove everything including volumes
docker-compose down -v

# Rebuild a single service
docker-compose up -d --build api
```

## Managing Schema Migrations

```bash
# Generate migration from model changes
alembic revision --autogenerate -m "describe change"

# Apply all pending migrations
alembic upgrade head

# Roll back one migration
alembic downgrade -1
```

## Role-Based Access Control

All routes require a valid Bearer token unless marked **public**. Roles are set at registration (`user` / `seller`) or granted by an admin (`admin`).

| Action                          | `user`      | `seller`          | `admin`    |
| ------------------------------- | ----------- | ----------------- | ---------- |
| Register / Login                | ✅ Public   | ✅ Public         | ✅ Public  |
| View products (list / search)   | ✅          | ✅                | ✅         |
| View single product             | ✅          | ✅                | ✅         |
| Create product                  | ❌          | ✅                | ✅         |
| Update own product              | ❌          | ✅ (owner only)   | ✅ (any)   |
| Soft-delete own product         | ❌          | ✅ (owner only)   | ✅ (any)   |
| Place an order                  | ✅          | ✅                | ✅         |
| View own orders                 | ✅          | ✅                | ✅         |
| Cancel own pending order        | ✅          | ✅                | ✅         |
| Update own profile              | ✅          | ✅                | ✅         |
| Delete own account              | ✅          | ✅                | ✅         |
| List all users                  | ❌          | ❌                | ✅         |
| Change any user's role          | ❌          | ❌                | ✅         |
| Health / metrics endpoints      | ✅ Public   | ✅ Public         | ✅ Public  |
