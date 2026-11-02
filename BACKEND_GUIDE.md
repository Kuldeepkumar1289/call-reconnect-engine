# Backend Guide: Smart Call Reconnect Engine

This guide explains the backend as it exists in this repository: what each part
does, how a call moves through the system, how to run and change it, and which
behaviors are not implemented yet. It is written as a learning guide, so it
explains the terms as well as the code structure.

> **Scope note:** This describes the current implementation, not a complete
> history of every past development decision. The repository has existing
> uncommitted changes; this guide documents the code currently present without
> attempting to reconstruct or replace deleted files.

## 1. What the backend does

The application is a Python web service built with **FastAPI**. Its core job is
to accept call events and choose an agent for an inbound call. It also records
call and agent state in **MySQL**, temporarily remembers dropped-call
reconnection details in **Redis**, and periodically releases agents whose
reconnection window has expired.

At a high level:

1. A telephony system sends an inbound-call request.
2. The backend first checks whether that call session was already handled.
3. If the customer's previous call dropped recently, the backend tries to
   reconnect the customer to the same agent.
4. Otherwise, it assigns an available agent or records the call as queued.
5. When a call disconnects, the backend either starts a reconnect window or
   marks the call complete.
6. A background loop expires old reconnect windows and releases agents.
7. Telemetry endpoints calculate aggregate call and agent statistics.

### Technology used

| Technology | Purpose in this project |
|---|---|
| Python | Backend programming language |
| FastAPI | HTTP API framework and OpenAPI documentation |
| Pydantic | Request validation and response serialization |
| SQLAlchemy | Python-to-SQL database mapping and queries |
| MySQL / PyMySQL | Persistent storage for agents, calls, and drop logs |
| Redis | Temporary storage for reconnect sessions with an expiration time |
| Alembic | Database schema migration framework |
| bcrypt | Password hashing helper |
| python-jose | JWT creation and decoding helper |
| Uvicorn | ASGI server used to run the FastAPI application |

## 2. How the code is organized

The backend is organized by responsibility. This separation helps keep HTTP
details, business rules, database structure, and configuration from becoming
one large file.

| Path | Responsibility |
|---|---|
| [`app/main.py`](app/main.py) | Creates the FastAPI app, configures middleware and routes, serves the frontend, and starts/stops the cleanup loop |
| [`app/api/v1/api.py`](app/api/v1/api.py) | Combines the version 1 API endpoint groups |
| [`app/api/v1/endpoints/`](app/api/v1/endpoints/) | Converts HTTP requests into service calls and HTTP responses |
| [`app/services/`](app/services/) | Implements agent, call-routing, reconnect, and telemetry business logic |
| [`app/models/`](app/models/) | SQLAlchemy definitions for database tables and enums |
| [`app/schemas/`](app/schemas/) | Pydantic request and response shapes |
| [`app/core/config.py`](app/core/config.py) | Reads settings from environment variables and `.env` |
| [`app/core/database.py`](app/core/database.py) | Creates the SQLAlchemy engine, session factory, and common DB dependency |
| [`app/core/redis.py`](app/core/redis.py) | Creates the Redis client and provides reconnect-session operations |
| [`app/core/security.py`](app/core/security.py) | Provides password hashing and JWT creation helpers |
| [`app/api/deps.py`](app/api/deps.py) | Contains a separate, currently unwired authentication/DB dependency |
| [`app/workers/cleanup_worker.py`](app/workers/cleanup_worker.py) | Expires pending drop records and releases held agents |
| [`alembic/`](alembic/) | Alembic migration environment and revision files |
| [`init_db.py`](init_db.py) | Creates tables from the SQLAlchemy model metadata |
| [`requirements.txt`](requirements.txt) | Python package requirements |

The project also has a `frontend/` directory. The FastAPI app serves its
`index.html` at `/` and mounts its files under `/static`; it is not the backend
API itself.

## 3. Request-to-database flow

For a typical API request, the flow is:

```text
HTTP request
    ↓
FastAPI endpoint (app/api/v1/endpoints/)
    ↓ validates request using a Pydantic schema
Service (app/services/)
    ↓ reads/writes through a SQLAlchemy Session
MySQL models (app/models/)
    ↓
HTTP response (usually serialized using a response schema)
```

The endpoint is the adapter between HTTP and the application. The service
contains the decision-making. The model describes how persistent data is stored.
The schema describes what callers are allowed to send or receive.

For example, `POST /api/v1/calls/inbound` validates an
`InboundCallRequest`, calls `CallService.route_inbound_call`, and serializes
the result as `CallRoutingResponse`.

### Database sessions

[`app/core/database.py`](app/core/database.py) builds a SQLAlchemy engine using
the configured database URL. `get_db()` creates one database session for a
request, yields it to the endpoint, and closes it afterward. The endpoint files
use this dependency.

The session is the unit through which SQLAlchemy performs queries and
transactions. A service typically modifies model objects, calls `commit()` to
persist those changes, and sometimes calls `refresh()` to reload generated
database values.

## 4. Data model: what is stored

The current SQLAlchemy models define three main tables.

### 4.1 `agents`

Defined in [`app/models/agent.py`](app/models/agent.py).

An agent represents a support representative who can receive calls.

| Field | Meaning |
|---|---|
| `id` | Database-generated agent identifier |
| `agent_code` | Unique human-readable agent code |
| `full_name` | Agent's display name |
| `email` | Unique email address |
| `hashed_password` | Password hash; the plaintext password is not returned by the response schema |
| `status` | Telephony availability state |
| `is_active` | Whether the agent is active for normal inbound assignment |
| `created_at`, `updated_at` | Creation and last-update timestamps |

The status values used by the API are `AVAILABLE`, `BUSY`, `ON_HOLD`,
`WRAP_UP`, and `OFFLINE`. `ON_CALL` is an enum alias for `BUSY` in the model.
The routing service assigns only agents whose status is `AVAILABLE` and whose
`is_active` flag is true.

### 4.2 `calls`

Defined in [`app/models/call.py`](app/models/call.py).

Each row represents one call session, including a reconnected call. The
`call_session_id` is unique, which lets the service recognize repeated inbound
requests for the same session.

Important fields:

- `customer_phone_number`: identifies the customer for reconnect matching.
- `assigned_agent_id`: optional link to the assigned agent. It is nullable so a
  queued call can exist without an agent.
- `call_status`: `INITIATED`, `RINGING`, `QUEUED`, `IN_PROGRESS`, `COMPLETED`,
  or `DROPPED`.
- `disconnect_reason`: records why the call ended, such as `NETWORK_FAILURE`
  or `NORMAL_CLEARING`.
- `is_reconnected_call`: marks a call created by the reconnect path.
- `previous_call_id`: links a reconnected call to the original call row.
- `created_at`, `started_at`, and `ended_at`: call timestamps.

The model has an agent relationship and a self-reference through
`previous_call_id`. The service currently creates an unassigned call with
`QUEUED` status when there is no available agent. The repository does not
currently include a queue-draining process that automatically assigns those
queued calls later.

### 4.3 `call_drop_logs`

Defined in [`app/models/drop_log.py`](app/models/drop_log.py).

This table tracks reconnect attempts for network-dropped calls.

| Field | Meaning |
|---|---|
| `original_call_id` | Call that dropped |
| `customer_phone_number` | Customer used to match a later inbound call |
| `assigned_agent_id` | Agent to hold for a possible reconnect |
| `dropped_at` | When the drop was recorded |
| `reconnect_window_expires_at` | Intended end of the reconnect window |
| `status` | `PENDING`, `RECONNECTED`, `EXPIRED`, or `FAILED` |
| `reconnected_at` | When reconnect succeeded, if it did |
| `time_taken_seconds` | Elapsed time from drop to reconnect |

The service starts a `PENDING` log on a network failure. A successful reconnect
changes it to `RECONNECTED`; the cleanup worker changes it to `EXPIRED` after
the Redis reconnect key disappears.

## 5. Request schemas and validation

Pydantic schemas under [`app/schemas/`](app/schemas/) define the HTTP data
contracts. FastAPI uses them to parse and validate JSON before calling the
endpoint.

Examples of current validation:

- `InboundCallRequest` requires a call session ID of 5–100 characters and a
  customer phone string of 10–20 characters.
- `AgentCreate` requires an agent code, name, valid email, and password of
  6–128 characters.
- `CallDisconnectRequest` requires a call session ID and a valid disconnect
  reason enum.
- `AgentResponse` uses `from_attributes=True`, so it can serialize an ORM
  `Agent` object into a response without manually building a dictionary.

Schemas are not database tables. They define how data crosses the API boundary;
the SQLAlchemy models define how data is persisted.

## 6. API reference

The versioned API prefix defaults to `/api/v1`. The assembled routes are
registered in [`app/api/v1/api.py`](app/api/v1/api.py).

### Calls

| Method and path | Purpose |
|---|---|
| `POST /api/v1/calls/inbound` | Route a new or repeated inbound call |
| `POST /api/v1/calls/disconnect` | Record a disconnect and either begin reconnect handling or complete the call |

**Inbound request**

```json
{
  "call_session_id": "CALL-UUID-98213",
  "customer_phone_number": "+919876543210"
}
```

The response includes the call session ID, customer phone number, assigned
agent ID and code, whether this is a reconnect, the original call ID (when
reconnected), and a human-readable routing message. When no agent is available,
the implementation uses `assigned_agent_id: 0` and `assigned_agent_code:
"UNASSIGNED"` in this response; the database call itself has a null agent ID and
`QUEUED` status.

**Disconnect request**

```json
{
  "call_session_id": "CALL-UUID-98213",
  "disconnect_reason": "NETWORK_FAILURE"
}
```

The disconnect reason must be one of `NORMAL_CLEARING`, `NETWORK_FAILURE`,
`AGENT_TIMEOUT`, or `UNKNOWN_DROP`.

### Agents

| Method and path | Purpose |
|---|---|
| `POST /api/v1/agents/` | Create an agent |
| `GET /api/v1/agents/` | List agents; supports `skip` and `limit` query parameters |
| `GET /api/v1/agents/{agent_id}` | Get one agent |
| `PATCH /api/v1/agents/{agent_id}` | Partially update name, email, or status |
| `PATCH /api/v1/agents/{agent_id}/status?new_status=AVAILABLE` | Set an agent's status |
| `POST /api/v1/agents/{agent_id}/release-hold` | Change an `ON_HOLD` agent to `AVAILABLE` |

The list endpoint defaults to `skip=0` and `limit=100`; `limit` is constrained
to 1–100. Creating an agent checks for an existing email and stores a bcrypt
hash of the provided password. The returned `AgentResponse` does not include
the password hash.

### Telemetry

| Method and path | Purpose |
|---|---|
| `GET /api/v1/telemetry/metrics` | Return call counts, rates, and average reconnect time |
| `GET /api/v1/telemetry/agents/occupancy` | Return agent counts and occupancy percentage |

These are aggregate database queries over the records currently stored; there
is no time-range query parameter.

### Application and documentation routes

| Method and path | Purpose |
|---|---|
| `GET /health` | Return a simple application-level health response |
| `GET /` | Serve `frontend/index.html` |
| `/static/...` | Serve static frontend files |
| `GET /docs` | FastAPI Swagger UI |
| `GET /api/v1/openapi.json` | OpenAPI schema |

The health endpoint reports the application as healthy; it does not currently
check MySQL or Redis connectivity.

## 7. Call routing and reconnect behavior

The routing implementation is in
[`app/services/call_service.py`](app/services/call_service.py).

### 7.1 Idempotent inbound requests

First, the service searches `calls` by `call_session_id`. If it finds a row, it
returns the existing assignment instead of creating another call. This is
called **idempotency**: retrying the same request should not create duplicate
records.

### 7.2 Reconnecting a dropped call

When a call disconnects because of `NETWORK_FAILURE` and has an assigned agent:

1. The call becomes `DROPPED` and gets an `ended_at` timestamp.
2. The agent becomes `ON_HOLD`, meaning it is being reserved for the customer.
3. Redis receives a key based on the customer's phone number. Its value
   contains the agent ID and original call ID.
4. Redis expires that key after `STICKY_WINDOW_SECONDS` (180 seconds by
   default).
5. A `PENDING` row is written to `call_drop_logs`.

When the same customer calls again while that Redis key still exists:

1. The service retrieves the stored agent and original call.
2. It creates a new `IN_PROGRESS` call assigned to the same agent.
3. The new call is marked as a reconnect and points back to the original call.
4. The pending drop log becomes `RECONNECTED`; the elapsed reconnect time is
   stored.
5. The Redis key is deleted and the agent becomes `BUSY`.

Redis is the short-lived lookup used to decide whether the reconnect window is
still open. MySQL keeps the durable call and drop history.

### 7.3 Normal completion and non-network disconnects

If the disconnect reason is not `NETWORK_FAILURE`, or there is no assigned
agent, the service marks the call `COMPLETED`. If an agent was assigned, that
agent returns to `AVAILABLE`.

The service also contains a `complete_call` method and a
`CallCompleteRequest` schema. At present, no API endpoint calls that method, so
it is not available as an HTTP operation.

### 7.4 No agent available

For a call that is neither an idempotent replay nor a reconnect, the service
locks and selects the first `AVAILABLE`, active agent. If one is found, the
agent becomes `BUSY` and the call becomes `IN_PROGRESS`. If none is found, the
call is saved with `QUEUED` status and no assigned agent.

The code records queued calls but does not yet implement a waiting queue,
position tracking, or automatic assignment when an agent later becomes
available.

## 8. Redis and the background cleanup worker

[`app/core/redis.py`](app/core/redis.py) creates a Redis connection pool and
provides `RedisSessionManager`. Its dropped-call key is prefixed with
`call_drop:` and keyed by customer phone number. The key's expiry is the source
of truth for whether the reconnect window is still active.

The cleanup loop is started by the FastAPI lifespan in
[`app/main.py`](app/main.py). Every 10 seconds by default, it:

1. Loads `PENDING` drop logs from MySQL.
2. Checks whether each customer's reconnect key still exists in Redis.
3. If the key has expired, marks the log `EXPIRED`.
4. If the associated agent is still `ON_HOLD`, changes the status to
   `AVAILABLE`.
5. Commits the database changes.

Database work is synchronous, so the async loop runs it through
`asyncio.to_thread` to avoid blocking the event loop. During application
shutdown, the task is cancelled and awaited.

The cleanup loop is also runnable as a module, but normally the application
starts it automatically. Running a separate copy at the same time is generally
unnecessary.

## 9. Telemetry calculations

[`app/services/telemetry_service.py`](app/services/telemetry_service.py)
calculates the following:

### System metrics

- `total_calls`: all rows in `calls`.
- `total_dropped`: calls whose status is `DROPPED`.
- `total_reconnected`: calls with `is_reconnected_call` set.
- `drop_rate_percentage`: `total_dropped / total_calls * 100`.
- `reconnect_success_rate_percentage`: `total_reconnected / total_dropped *
  100`.
- `avg_reconnection_time_seconds`: average `time_taken_seconds` for drop logs
  with `RECONNECTED` status.

When a denominator is zero, the corresponding rate is returned as `0.0`.

### Agent occupancy

- `total_agents`: all agent rows.
- `available_agents`: agents with `AVAILABLE` status.
- `busy_agents`: agents with `BUSY` status.
- `on_hold_for_reconnect`: agents with `ON_HOLD` status.
- `occupancy_rate_percentage`: `(busy_agents + on_hold_agents) / total_agents *
  100`.

These calculations use the full database history and current agent states.

## 10. Configuration

Settings are defined in [`app/core/config.py`](app/core/config.py) using
Pydantic Settings. Values can be supplied as environment variables or through a
root `.env` file. `DATABASE_URL`, when provided, takes precedence over the
individual MySQL settings.

| Setting | Purpose | Default |
|---|---|---|
| `PROJECT_NAME` | FastAPI application title and health response name | `Smart Call Reconnect Engine` |
| `API_V1_STR` | API version prefix | `/api/v1` |
| `DATABASE_URL` | Full SQLAlchemy connection string; overrides MySQL components | unset |
| `MYSQL_USER` | MySQL user | `root` |
| `MYSQL_PASSWORD` | MySQL password | `rootpassword` |
| `MYSQL_SERVER` | MySQL hostname | `mysql` |
| `MYSQL_PORT` | MySQL port | `3306` |
| `MYSQL_DB` | MySQL database name | `call_reconnect_db` |
| `REDIS_HOST` | Redis hostname | `redis` |
| `REDIS_PORT` | Redis port | `6379` |
| `REDIS_DB` | Redis logical database number | `0` |
| `REDIS_PASSWORD` | Redis password; blank means no password is supplied | blank |
| `STICKY_WINDOW_SECONDS` | Redis reconnect-key lifetime | `180` |
| `JWT_SECRET_KEY` | Signing key for JWT helper functions | insecure development fallback |
| `JWT_ALGORITHM` | JWT signing algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Default token lifetime | `1440` |

For local development, set the database and Redis values to services that are
reachable from the process. Do not copy real credentials into documentation or
commit them to source control. Configure a strong `JWT_SECRET_KEY` in any
environment that handles real traffic; the fallback is only suitable for
development.

## 11. Running the application

The repository lists dependencies in [`requirements.txt`](requirements.txt).
With Python and the project's dependencies installed, start the API from the
repository root:

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000` by default. Useful pages:

- `http://127.0.0.1:8000/docs` — interactive Swagger UI.
- `http://127.0.0.1:8000/health` — application health response.
- `http://127.0.0.1:8000/` — served frontend.

MySQL and Redis need to be running and configured before exercising database
and reconnect operations. The project does not include a service orchestration
file in the repository root.

### Creating database tables

[`init_db.py`](init_db.py) calls SQLAlchemy `metadata.create_all()`. It is a
simple way to create tables that do not yet exist from the current model
definitions. It does **not** alter already-existing tables to match model
changes.

Alembic is configured in [`alembic/env.py`](alembic/env.py) to use the same
database settings and model metadata. The current revision
[`3db2a57e2f16_sync_models_and_enums.py`](alembic/versions/3db2a57e2f16_sync_models_and_enums.py)
alters enum columns on existing `agents` and `calls` tables; it is not a
complete initial schema-creation migration. Before applying it to an existing
database, inspect the target schema and take a backup. Do not assume that
running `alembic upgrade head` creates a fresh database from nothing.

## 12. Security and implementation boundaries

These details are important when understanding what the backend currently
guarantees:

- The agent and call endpoints currently do not depend on
  `get_current_agent`; they are not protected by a login flow in the API
  routing shown in this repository.
- Password hashing and JWT creation/decoding helpers exist, and agent login
  request data is modeled, but there is no registered login endpoint in the
  current API router.
- [`app/api/deps.py`](app/api/deps.py) appears to be unfinished or stale: it
  imports `SessionLocal` from `app.core.database`, but that module currently
  defines `DatabaseSessionLocal`; it also imports `app.schemas.token`, which is
  not present in the current schema directory. This dependency is not used by
  the registered endpoint files, but importing it as-is will fail until those
  references are reconciled.
- CORS currently allows all origins, methods, and headers while also allowing
  credentials. Production deployments should configure an explicit trusted
  origin list.
- The default MySQL password and JWT signing key are development fallbacks,
  not production secrets.
- `/health` confirms that the FastAPI process responds; it does not verify
  that MySQL or Redis is ready.
- MySQL writes and Redis operations are separate operations. They are not one
  atomic transaction, so an infrastructure failure between them can leave the
  two stores temporarily inconsistent.
- Agent statuses and call statuses are stored using enums. When changing enum
  values, update the models and database schema together through a reviewed
  migration.

These are descriptions of current behavior, not claims that all of these
concerns have already been addressed.

## 13. A practical way to explore the code

To understand one behavior from end to end, follow the same order the request
takes:

1. Start at the route in `app/api/v1/endpoints/`.
2. Read its request and response schema in `app/schemas/`.
3. Follow the service function it calls in `app/services/`.
4. Check the models in `app/models/` to see which fields are persisted.
5. Check `app/core/redis.py` if the behavior uses temporary reconnect state.
6. Check `app/workers/cleanup_worker.py` if the behavior changes when time
   passes.

For example, to understand a network-drop reconnect, start with the disconnect
endpoint, follow `CallService.handle_call_disconnect`, inspect the `Call` and
`CallDropLog` models, then follow the inbound endpoint into
`CallService.route_inbound_call` and the cleanup worker.
