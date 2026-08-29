# GradMatch

GradMatch is a Web-first monorepo with a Django API, headless authentication, and a Next.js product shell. Shared TypeScript packages remain platform-neutral so a future Expo application can reuse its domain rules, tokens, and generated API clients.

## Workspace

- `apps/web`: minimal Next.js App Router foundation page
- `packages/api-client`: generated TypeScript clients for the Django Ninja core API and allauth Headless API
- `packages/domain`: shared TypeScript domain contracts
- `packages/design-tokens`: typed semantic design tokens with no browser dependencies
- `services/api`: uv-managed Django modular monolith with Django Ninja, Admin, and allauth Headless

## Commands

- `pnpm dev`: start the monorepo development processes
- `pnpm build`: build all TypeScript workspace packages and the web app
- `pnpm lint`: run Biome across JavaScript, TypeScript, JSON, and Markdown files
- `pnpm typecheck`: run strict TypeScript checks across the workspace
- `pnpm test`: run workspace smoke tests
- `pnpm format:check`: verify formatting with Biome
- `pnpm generate:api`: export the core and auth OpenAPI specifications, then regenerate TypeScript clients
- `pnpm check:api-drift`: regenerate the clients and fail when committed contract artifacts drift
- `pnpm check:compose`: parse Compose, inspect Caddy routing, and verify container service/health/secret boundaries without starting Docker

## Python Service

Use portable `uv` commands scoped to `services/api`:

```powershell
python -m uv --directory services/api lock
python -m uv --directory services/api run ruff check .
python -m uv --directory services/api run pyright
python -m uv --directory services/api run pytest
```

If `uv` is on your `PATH`, the same root-safe commands also work as:

```powershell
uv --directory services/api lock
uv --directory services/api run ruff check .
uv --directory services/api run pyright
uv --directory services/api run pytest
```

## Authentication and API contracts

- `GET /api/v1/health/live`, `GET /api/v1/health/ready`, and `GET /api/v1/meta` provide the initial system contract.
- `/_allauth/*` supplies email sign-up, verification, password login, one-time-code login, logout, and Headless OpenAPI documentation.
- Browser clients authenticate with secure HttpOnly session cookies; future mobile clients use allauth's `X-Session-Token`. GradMatch does not issue JWTs.
- Local email is delivered to the SMTP host defined by `EMAIL_SMTP_*`; Docker Compose will point those variables at Mailpit.

## Local container stack

Docker Compose is the first deployment target: Caddy provides one browser origin, with Django handling API, allauth, admin, and static/media paths while Next.js handles the remaining pages. PostgreSQL, Redis, MinIO, Mailpit, Celery worker/beat, and a one-shot migration service remain internal to the stack.

```powershell
Copy-Item .env.example .env
docker compose up --build --wait
```

Open `http://localhost` for GradMatch and `http://localhost:8025` for Mailpit. The `migrate` one-shot service applies migrations and collects static files into the shared read-only API volume before API, worker, or beat processes start. Stop the stack with `docker compose down`; add `--volumes` only when you intentionally want to discard local PostgreSQL, MinIO, and static-file data.

The committed `.env.example` values are development-only placeholders. Keep the copied `.env` local, use a long unique Django secret for any deployment-like environment, and never commit real credentials.

## Ingestion foundation

- `gradmatch.ingestion` is a Celery-driven modular-monolith app. `ingestion.run_source` records each run and retries operational failures through Celery.
- The first `smoke-fixture` source reads only `services/api/tests/fixtures/sample-source.html`; it never requests a public website.
- Raw source bytes are de-duplicated by SHA-256 and stored through an S3-compatible artifact-store boundary. Future adapters can use the HTTPX or Playwright fetcher boundaries without changing the run lifecycle.

## Scope Notes

The mobile app is intentionally absent in this repository stage. Expo support is deferred until a later task.
