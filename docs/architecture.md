# GradMatch architecture baseline

## Purpose and boundaries

GradMatch starts as a Web-first modular monolith. `apps/web` owns the Next.js presentation layer; `services/api` owns Django business persistence, authentication, administration, API contracts, and background ingestion. This is intentionally not a microservice system.

`packages/domain` contains platform-neutral rules and query definitions. `packages/design-tokens` contains semantic design values only. `packages/api-client` is generated from Django Ninja and allauth OpenAPI specifications; browser, Web server, and the future Expo app consume these clients instead of copying DTOs.

## Browser and API path

The browser has one Caddy origin. `/api/*`, `/_allauth/*`, `/accounts/*`, `/admin/*`, `/static/*`, and `/media/*` go to Django. All other paths go to Next.js. Browser requests stay relative to this origin so Django can use Secure, HttpOnly, SameSite cookies without CORS configuration. Server Components use `GRADMATCH_API_BASE_URL` to call the internal API service.

Authentication is Django allauth Headless. Browsers use session cookies; a future mobile app uses allauth `X-Session-Token`, not JWT. Email verification is mandatory, and the product currently supports password plus one-time-email-code login. Phone, WeChat, and QQ are extension boundaries only.

## Background data boundary

Celery worker and beat share the Django codebase and Redis broker. Ingestion adapters create a `DataSource` run, persist an immutable raw artifact by content hash, then record parsed results or a sanitized error. The only current adapter reads a local fixture; CI and unit tests must never request public ingestion sites.

## Deployment shape

Docker Compose is the first single-host target. PostgreSQL, Redis, MinIO, and Mailpit are internal dependencies. A one-shot migration service is the only process that runs migrations and collects static assets; the API reads its shared static-files volume. Caddy holds its own named data/configuration volumes. Kubernetes, vendor-specific deployment services, GraphQL, and external search are explicit non-goals.

## Mobile migration path

No Expo UI is built yet. When it is, Expo/React Native consumes `packages/domain`, `packages/design-tokens`, and `packages/api-client`; platform-specific components remain in the mobile app. This keeps future Android and iOS work from duplicating request types, validation rules, or product semantics.
