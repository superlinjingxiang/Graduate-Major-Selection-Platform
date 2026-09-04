# GradMatch First Vertical Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` to execute this plan task-by-task, with a fresh implementer and review pass for every task.

**Goal:** Deliver the first trustworthy, end-to-end GradMatch decision slice for the frozen 2027 Beijing full-time computer-related unified-exam pilot, from source evidence and deterministic eligibility through comparison, guest decision snapshots, corrections, and idempotent recomputation.

**Architecture:** Extend the existing Django modular monolith with evidence, catalog, advising, and support modules. Keep PostgreSQL as the source of truth, Redis/Celery for asynchronous work, S3-compatible storage for immutable raw blobs, Django Ninja for versioned APIs, generated TypeScript clients for contracts, and Next.js Server Components plus narrowly scoped Client Components for the Web experience. Decision results are versioned and reproducible from immutable inputs; production and synthetic fixture data are isolated at both storage and service boundaries.

**Tech Stack:** Django 5.2 LTS, Django Ninja, django-allauth Headless, PostgreSQL, Redis, Celery, S3-compatible object storage, Python 3.12, uv, pytest, Ruff, Pyright, Next.js App Router, React, TypeScript strict, pnpm, Turborepo, Zod, TanStack Query, Tailwind CSS.

**Spec:** `docs/product-requirements.md`, `docs/architecture.md`, `docs/research/pilot-scope-2027-v1.md`, and `docs/research/validation-protocol-v1.md`.

## Progress checkpoint — 2026-09-04

Tasks 1–8 have implementation commits; Task 9 has test scaffolding only and currently fails because its pages/components do not exist. Task 10 and release verification remain pending. See the [progress record](../../progress/2026-09-04-first-vertical-slice.md) for fresh checks, known gaps, and continuation priorities. This plan is not complete. Resolve Web paths below against the actual `apps/web/src/app`, `apps/web/src/features`, and `apps/web/src/lib` layout.

## Global constraints

- The only production pilot is target year 2027, Beijing, full-time, unified-exam, computer-related programs, at shortlist-convergence stage.
- Freeze all ten planned annual-offering IDs from the pilot manifest. The engineering smoke slice is exactly:
  - `ao_2027_bupt_081200_ft_unified_plan01`
  - `ao_2027_bit_085404_ft_unified_plan01`
  - `ao_2027_bjut_085410_ft_unified_plan01`
- Until reviewed 2027 official evidence and a complete published rule set exist, production eligibility must be `needs_confirmation`; no placeholder fact may become a user conclusion.
- Synthetic and historical-reference data must carry an explicit namespace and `reference_year`. Synthetic `reference_year=2026` fixtures are test-only and must never appear in production serializers, coverage metrics, recommendation counts, or user-facing conclusions.
- AI recommendations, payment, paid rankings, mobile screens, real-site crawling, and external search engines remain disabled.
- Public pages must not expose infrastructure health, environment names, build versions, internal review notes, token digests, source-storage keys, or implementation details.
- Every behavior change starts with a failing test. Run the narrow test before implementation, then the affected suite, then the repository verification gate.
- OpenAPI is the contract source. Regenerate `packages/api-client`; do not hand-write duplicate TypeScript DTOs.
- Preserve existing user files and unrelated worktree changes. Each task commits only its own files.

## Task 1: Make the Python and OpenAPI toolchain portable on this Windows checkout

**Files:**

- Create: `scripts/python-runtime.mjs`
- Create: `scripts/python-runtime.test.mjs`
- Create: `scripts/check-python.mjs`
- Modify: `scripts/generate-api.mjs`
- Modify: `package.json`
- Test: `scripts/python-runtime.test.mjs`

### Step 1: Write the failing runtime-resolution tests

Export a pure resolver that accepts injected filesystem and environment values. Cover this order:

1. `services/api/.venv/Scripts/python.exe` on Windows or `.venv/bin/python` on POSIX.
2. `uv run --project services/api python` when `uv` is available.
3. `python`/`python3` only as the final fallback.

The test contract should look like:

```js
test("prefers the repository virtualenv on Windows", () => {
  const runtime = resolvePythonRuntime({
    platform: "win32",
    root: "E:/GradMatch",
    exists: (candidate) => candidate.endsWith("services/api/.venv/Scripts/python.exe"),
    commandExists: () => false,
  });

  assert.deepEqual(runtime, {
    command: "E:/GradMatch/services/api/.venv/Scripts/python.exe",
    prefixArgs: [],
  });
});
```

Run: `node --test scripts/python-runtime.test.mjs`

Expected: FAIL because the resolver does not exist.

### Step 2: Implement the resolver and shared command runner

`scripts/python-runtime.mjs` must export:

```js
export function resolvePythonRuntime(options = {}) {}
export function runPython(args, options = {}) {}
```

Use `spawnSync` with inherited stdio, preserve the child exit code, and never require a globally installed `uv` when the repository virtualenv exists.

### Step 3: Route generation and Python checks through the shared runtime

- Change `scripts/generate-api.mjs` so `services/api/scripts/export_openapi.py` runs through `runPython`.
- Add `scripts/check-python.mjs` to execute, from `services/api`:
  - `python -m pytest -p no:cacheprovider`
  - `python -m ruff check src tests`
  - `python -m pyright --pythonpath <resolved-python> src tests`
  - `python manage.py makemigrations --check --dry-run` with `DJANGO_SETTINGS_MODULE=gradmatch.config.settings_test`
- Add package scripts `test:tooling` and `check:python`; include them in the root `test`/`check` flow without duplicating execution.

### Step 4: Verify and commit

Run:

```powershell
node --test scripts/python-runtime.test.mjs
pnpm check:python
pnpm check:api-drift
```

Expected: all pass on this host even though global `python` and `uv` are unavailable.

Commit: `fix: make python tooling use project runtime`

## Task 2: Separate immutable raw blobs from every source access

**Files:**

- Modify: `services/api/src/gradmatch/ingestion/models.py`
- Modify: `services/api/src/gradmatch/ingestion/admin.py`
- Modify: `services/api/src/gradmatch/ingestion/runner.py`
- Create: `services/api/src/gradmatch/ingestion/migrations/0002_rawblob_sourcefetch.py`
- Modify: `services/api/tests/ingestion/test_runner.py`
- Create: `services/api/tests/ingestion/test_models.py`

### Step 1: Write failing provenance tests

Specify two independent records:

```python
class RawBlob(models.Model):
    content_hash = models.CharField(max_length=64, unique=True)
    storage_key = models.CharField(max_length=512, unique=True)
    byte_size = models.PositiveBigIntegerField()
    content_type = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class SourceFetch(models.Model):
    source = models.ForeignKey(DataSource, on_delete=models.PROTECT)
    run = models.ForeignKey(IngestionRun, on_delete=models.CASCADE, related_name="fetches")
    source_url = models.URLField(max_length=2048)
    requested_at = models.DateTimeField()
    fetched_at = models.DateTimeField(null=True, blank=True)
    http_status = models.PositiveSmallIntegerField(null=True, blank=True)
    etag = models.CharField(max_length=512, blank=True)
    last_modified = models.CharField(max_length=512, blank=True)
    status = models.CharField(max_length=24)
    blob = models.ForeignKey(RawBlob, null=True, on_delete=models.PROTECT)
    error_summary = models.TextField(blank=True)
```

Tests must prove:

- Two successful fetches of identical bytes create one `RawBlob` and two `SourceFetch` rows.
- Each fetch retains URL, run, timestamps, status, and response metadata.
- A failed access still creates a `SourceFetch` without a blob.
- Existing `RawArtifact` data is migrated before the old table is removed.

Run: `services\api\.venv\Scripts\python.exe -m pytest -p no:cacheprovider services/api/tests/ingestion -q`

Expected: FAIL against the current single-record artifact model.

### Step 2: Implement the schema, migration, and runner behavior

Hash bytes with SHA-256 before upload. Reuse the blob row and object key when the hash already exists, but always create a new access row. Store no fetched page body directly in PostgreSQL.

### Step 3: Verify and commit

Run:

```powershell
services\api\.venv\Scripts\python.exe -m pytest -p no:cacheprovider services/api/tests/ingestion -q
pnpm check:python
```

Commit: `feat: preserve source fetch provenance`

## Task 3: Add the frozen pilot catalog and read APIs

**Files:**

- Create: `services/api/src/gradmatch/catalog/__init__.py`
- Create: `services/api/src/gradmatch/catalog/apps.py`
- Create: `services/api/src/gradmatch/catalog/models.py`
- Create: `services/api/src/gradmatch/catalog/admin.py`
- Create: `services/api/src/gradmatch/catalog/api.py`
- Create: `services/api/src/gradmatch/catalog/seed.py`
- Create: `services/api/src/gradmatch/catalog/migrations/0001_initial.py`
- Create: `services/api/src/gradmatch/catalog/migrations/0002_seed_pilot_manifest.py`
- Modify: `services/api/src/gradmatch/config/settings.py`
- Modify: `services/api/src/gradmatch/system/api.py`
- Create: `services/api/tests/catalog/test_manifest.py`
- Create: `services/api/tests/catalog/test_api.py`

### Step 1: Write failing manifest and API tests

Create these contracts:

```python
class CoverageManifest(models.Model):
    key = models.SlugField(unique=True)
    version = models.PositiveIntegerField()
    target_year = models.PositiveSmallIntegerField()
    scope = models.JSONField()
    frozen_at = models.DateTimeField()


class AnnualOffering(models.Model):
    id = models.CharField(primary_key=True, max_length=96)
    target_year = models.PositiveSmallIntegerField()
    institution = models.ForeignKey("Institution", on_delete=models.PROTECT)
    taxonomy_node = models.ForeignKey("TaxonomyNode", on_delete=models.PROTECT)
    title = models.CharField(max_length=256)
    degree_type = models.CharField(max_length=24)
    study_mode = models.CharField(max_length=24)
    admission_pathway = models.CharField(max_length=32)
    publication_status = models.CharField(max_length=32)
```

Also add `Institution`, `TaxonomyRevision`, `TaxonomyNode`, and ordered `ManifestEntry(engineering_slice: bool)` models.

Tests must assert:

- The migration seeds exactly the ten IDs in `pilot-scope-2027-v1.md`.
- Exactly the three frozen engineering IDs have `engineering_slice=True`.
- Every seeded offering is `target_year=2027`, `full_time`, `unified_exam`, and `pending_publication`.
- `GET /api/v1/pilot-scope`, `/taxonomy`, `/offerings`, and `/offerings/{id}` expose public catalog fields only.
- Filtering cannot escape the frozen manifest.
- No fixture namespace or 2026 value is returned.

Run: `services\api\.venv\Scripts\python.exe -m pytest -p no:cacheprovider services/api/tests/catalog -q`

Expected: FAIL because the catalog module does not exist.

### Step 2: Implement schema, frozen data migration, and router

Mount a catalog router beneath the existing `/api/v1` Ninja API. Return `404` for IDs outside the active manifest rather than leaking catalog existence.

### Step 3: Verify and commit

Run:

```powershell
services\api\.venv\Scripts\python.exe -m pytest -p no:cacheprovider services/api/tests/catalog -q
pnpm check:python
```

Commit: `feat: add frozen pilot catalog`

## Task 4: Add reviewable evidence and deterministic rule revisions

**Files:**

- Create: `services/api/src/gradmatch/advising/__init__.py`
- Create: `services/api/src/gradmatch/advising/apps.py`
- Create: `services/api/src/gradmatch/advising/models.py`
- Create: `services/api/src/gradmatch/advising/publication.py`
- Create: `services/api/src/gradmatch/advising/rules.py`
- Create: `services/api/src/gradmatch/advising/admin.py`
- Create: `services/api/src/gradmatch/advising/migrations/0001_initial.py`
- Modify: `services/api/src/gradmatch/config/settings.py`
- Create: `services/api/tests/advising/test_publication.py`
- Create: `services/api/tests/advising/test_rules.py`

### Step 1: Write failing publication-boundary tests

Add immutable/versioned records for:

- `SourceDocumentRevision` linked to `SourceFetch`.
- `EvidenceClaimRevision` linked to one offering and field key.
- `ReviewDecision` with actor, outcome, and note.
- `PublicationEvent` identifying the exact approved claim revision.
- `RuleSetRevision` with namespace (`production` or `test_fixture`), target year, reference year, publication state, and completeness flag.
- `EligibilityRule` with fact key, operator (`equals`, `in`, `gte`, `is_true`), expected JSON value, reason code, and evidence usages.
- `RuleEvidenceUsage` joining a rule to the exact claim revisions used.

Tests must prove:

- An unreviewed claim cannot be published.
- A synthetic source cannot be published into a production rule set.
- A `reference_year=2026` rule set cannot use the production namespace.
- A production 2027 rule cannot become current without at least one approved, published 2027 claim.
- Published records are append-only; corrections create new revisions.

Run: `services\api\.venv\Scripts\python.exe -m pytest -p no:cacheprovider services/api/tests/advising/test_publication.py services/api/tests/advising/test_rules.py -q`

Expected: FAIL because advising publication does not exist.

### Step 2: Implement publication and fixture guards

Expose service functions, not model-side implicit mutation:

```python
def publish_claim(*, claim_id: int, reviewer, now) -> PublicationEvent: ...
def publish_rule_set(*, rule_set_id: int, reviewer, now) -> RuleSetRevision: ...
def evaluate_rule(rule: EligibilityRule, facts: dict[str, object]) -> bool | None: ...
```

Use database constraints where possible and repeat safety checks inside atomic service transactions.

### Step 3: Verify and commit

Run the narrow tests, then `pnpm check:python`.

Commit: `feat: add evidence and rule publication controls`

## Task 5: Implement fact-set revisions and three-state eligibility

**Files:**

- Modify: `services/api/src/gradmatch/advising/models.py`
- Create: `services/api/src/gradmatch/advising/eligibility.py`
- Create: `services/api/src/gradmatch/advising/api.py`
- Create: `services/api/src/gradmatch/advising/migrations/0002_fact_sets_eligibility.py`
- Modify: `services/api/src/gradmatch/system/api.py`
- Create: `services/api/tests/advising/test_eligibility.py`
- Create: `services/api/tests/advising/test_fact_set_api.py`

### Step 1: Write failing deterministic assessment tests

Add:

```python
class FactSet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)


class FactSetRevision(models.Model):
    fact_set = models.ForeignKey(FactSet, on_delete=models.CASCADE, related_name="revisions")
    version = models.PositiveIntegerField()
    confirmed_facts = models.JSONField()
    input_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)


class EligibilityAssessment(models.Model):
    offering = models.ForeignKey(AnnualOffering, on_delete=models.PROTECT)
    fact_revision = models.ForeignKey(FactSetRevision, on_delete=models.PROTECT)
    rule_set = models.ForeignKey(RuleSetRevision, null=True, on_delete=models.PROTECT)
    status = models.CharField(max_length=32)
    reasons = models.JSONField()
    input_hash = models.CharField(max_length=64)
```

Required behavior:

- `ineligible` when a complete published rule set has a confirmed failed hard rule.
- `eligible` only when every applicable hard rule is known and passes.
- `needs_confirmation` for missing facts, missing evidence, incomplete/unpublished rules, or all current seeded production offerings.
- Identical canonical inputs produce the same hash and reasons ordering.
- Test-fixture rules can be passed only by an explicit service-only `allow_test_fixture=True`; the production API never exposes that switch.
- API endpoints `POST /api/v1/fact-sets` and `POST /api/v1/eligibility-assessments` reject unknown fact keys and return stable reason codes.

### Step 2: Implement and verify

Keep human-readable copy out of persistence; persist stable reason codes plus evidence version IDs.

Run:

```powershell
services\api\.venv\Scripts\python.exe -m pytest -p no:cacheprovider services/api/tests/advising/test_eligibility.py services/api/tests/advising/test_fact_set_api.py -q
pnpm check:python
```

Commit: `feat: add deterministic eligibility assessments`

## Task 6: Add versioned comparisons and guest decision snapshots

**Files:**

- Modify: `services/api/src/gradmatch/advising/models.py`
- Create: `services/api/src/gradmatch/advising/comparison.py`
- Create: `services/api/src/gradmatch/advising/capabilities.py`
- Modify: `services/api/src/gradmatch/advising/api.py`
- Create: `services/api/src/gradmatch/advising/migrations/0003_comparisons_snapshots.py`
- Create: `services/api/tests/advising/test_comparison.py`
- Create: `services/api/tests/advising/test_guest_capability.py`
- Create: `services/api/tests/advising/test_snapshot_api.py`

### Step 1: Write failing comparison and security tests

Add stable request records plus immutable result revisions:

- `GuestSession(token_digest, expires_at, owner, claimed_at)`; only the SHA-256 digest is stored.
- `ComparisonRun` linked to fact revision, frozen manifest, owner or guest session.
- `ComparisonRunResult(version, result, result_hash, trigger_publication_event)`.
- `DecisionSnapshot` linked to an exact result revision and one of:
  - `shortlist_ready`
  - `no_suitable_offering`
  - `awaiting_official_information`
  - `postpone_application`

Tests must prove:

- The current frozen pilot produces `awaiting_official_information`, never a fabricated shortlist.
- Ordering and hashes are deterministic.
- `POST /comparison-runs`, `GET /comparison-runs/{id}`, `POST /decision-snapshots`, and `GET /decision-snapshots/{id}` enforce ownership.
- A random 256-bit capability is placed only in a `Secure`, `HttpOnly`, `SameSite=Lax` cookie with a short expiration; the database stores only its digest.
- Knowing a UUID is insufficient to access another guest snapshot.
- Claiming via `POST /decision-snapshots/{id}/claim` requires both an authenticated session and the valid capability, assigns ownership, and revokes/rotates the guest token.
- Expired or replayed capabilities fail.

### Step 2: Implement and verify

Use `secrets.token_urlsafe(32)`, `hmac.compare_digest`, and atomic claim transactions. Never serialize token digests or internal result inputs.

Run the new advising tests, then `pnpm check:python`.

Commit: `feat: add secure guest decision snapshots`

## Task 7: Add corrections, audit events, outbox publication, and idempotent recomputation

**Files:**

- Create: `services/api/src/gradmatch/support/__init__.py`
- Create: `services/api/src/gradmatch/support/apps.py`
- Create: `services/api/src/gradmatch/support/models.py`
- Create: `services/api/src/gradmatch/support/services.py`
- Create: `services/api/src/gradmatch/support/tasks.py`
- Create: `services/api/src/gradmatch/support/api.py`
- Create: `services/api/src/gradmatch/support/admin.py`
- Create: `services/api/src/gradmatch/support/migrations/0001_initial.py`
- Modify: `services/api/src/gradmatch/config/settings.py`
- Modify: `services/api/src/gradmatch/system/api.py`
- Create: `services/api/tests/support/test_corrections.py`
- Create: `services/api/tests/support/test_recomputation.py`

### Step 1: Write failing lifecycle and idempotency tests

Model:

- `CorrectionCase` with offering, field key, proposed source URL, explanation, state, submitter, and timestamps.
- `AuditEvent` append-only actor/action/target metadata.
- `OutboxEvent` unique event key, payload, publication time, processing state.
- `JobExecution` unique `(event_key, handler_name)` for idempotency.
- `SnapshotUpdate` linking an old snapshot/result to the newly computed result and stable diff payload.

Required behavior:

- Anonymous and signed-in users can submit a correction without seeing reviewer notes.
- Only staff may review, accept, publish, or reject.
- Accepting a correction creates a new evidence revision; publication and outbox creation occur in one transaction.
- Processing the same event twice creates exactly one new `ComparisonRunResult` and one `SnapshotUpdate` per affected run.
- The original snapshot/result remains immutable and readable.
- `POST /corrections` and `GET /corrections/{id}` expose only the submitter-safe status.

### Step 2: Implement and verify

The Celery task must call an idempotent domain handler; tests call that handler synchronously. Select affected runs from persisted evidence-version usages, not a broad full-table recompute.

Run the support tests, then the full Python gate.

Commit: `feat: add correction publication workflow`

## Task 8: Regenerate API clients and expose platform-neutral domain contracts

**Files:**

- Modify: `packages/api-client/src/generated/core.ts`
- Modify: `packages/api-client/src/core-client.ts`
- Modify: `packages/api-client/src/index.ts`
- Modify: `packages/domain/package.json`
- Create: `packages/domain/src/pilot.ts`
- Create: `packages/domain/src/decision.ts`
- Modify: `packages/domain/src/index.ts`
- Create: `packages/domain/test/pilot.test.ts`
- Create: `packages/domain/test/decision.test.ts`

### Step 1: Write failing cross-platform contract tests

Domain modules may depend on generated API types, Zod, and plain TypeScript only. They must not import DOM, Next.js, React, or React Native APIs.

Tests cover:

- Parsing the public pilot-scope response.
- Parsing eligibility statuses and all four decision outcomes.
- Rejecting an unexpected status or leaked internal field.
- Stable reason-code-to-public-copy mapping, with `needs_confirmation` language that explains uncertainty without implying acceptance.

### Step 2: Regenerate, implement, and verify

Run:

```powershell
pnpm generate:api
pnpm --filter @gradmatch/domain test
pnpm typecheck
pnpm check:api-drift
```

Commit: `feat: publish generated decision contracts`

## Task 9: Build the Web pilot decision flow

**Files:**

- Read before editing: `apps/web/node_modules/next/dist/docs/01-app/01-getting-started/05-server-and-client-components.md`
- Read before editing: the relevant Next.js forms/mutations guide under `apps/web/node_modules/next/dist/docs`
- Create: `apps/web/app/match/page.tsx`
- Create: `apps/web/app/match/loading.tsx`
- Create: `apps/web/app/match/error.tsx`
- Create: `apps/web/app/match/result/[id]/page.tsx`
- Create: `apps/web/components/match/fact-form.tsx`
- Create: `apps/web/components/match/offering-list.tsx`
- Create: `apps/web/components/match/decision-summary.tsx`
- Create: `apps/web/lib/pilot-api.ts`
- Modify: `apps/web/app/page.tsx`
- Modify: `apps/web/app/globals.css`
- Create: `apps/web/test/match-page.test.tsx`
- Create: `apps/web/test/fact-form.test.tsx`
- Create: `apps/web/test/decision-summary.test.tsx`

### Step 1: Write failing user-flow tests

Test the visible contract:

- The server-rendered `/match` page loads pilot scope and offerings through the generated client.
- The form asks only confirmed, necessary facts and labels optional/unknown values clearly.
- Submission creates a fact-set revision, eligibility assessment, comparison, and snapshot in sequence.
- Current seed data ends at “等待 2027 官方信息”，with the next action and evidence freshness shown; it never displays a ranked recommendation.
- The results page presents the four possible outcomes, reason codes as plain Chinese copy, source/evidence status, and a correction entry point.
- No platform status, environment, build version, storage key, review note, or token value appears in rendered output.
- Keyboard focus, labels, errors, contrast, reduced motion, and mobile-width layout are covered by component assertions where practical.

### Step 2: Implement with server-first rendering

Keep catalog loading in Server Components. Make only the form and interactive disclosure controls Client Components. Use design tokens and restrained motion; do not add a heavy animation library.

### Step 3: Verify and commit

Run:

```powershell
pnpm --filter @gradmatch/web test
pnpm --filter @gradmatch/web typecheck
pnpm --filter @gradmatch/web build
```

Commit: `feat: add pilot decision flow`

## Task 10: Prove the vertical slice and document native local operation

**Files:**

- Create: `services/api/tests/e2e/test_pilot_vertical_slice.py`
- Create: `scripts/native-status.mjs`
- Modify: `README.md`
- Modify: `.env.example`
- Modify: `docs/architecture.md`
- Modify: `docs/product-requirements.md`

### Step 1: Write the failing end-to-end test

The test must execute, without external network access:

1. Load the frozen pilot manifest.
2. Create a guest fact set.
3. Assess all three engineering offerings as `needs_confirmation` under current production data.
4. Create a deterministic comparison and `awaiting_official_information` snapshot.
5. Claim the snapshot with a verified account plus capability.
6. Submit and staff-publish a correction backed by a local fixture source.
7. Process the outbox event twice.
8. Assert one recomputed result/update, preserved old result, and no fixture leakage.

Run: `services\api\.venv\Scripts\python.exe -m pytest -p no:cacheprovider services/api/tests/e2e/test_pilot_vertical_slice.py -q`

Expected: FAIL until all pieces are integrated.

### Step 2: Add native-operation diagnostics and documentation

`scripts/native-status.mjs` must check, without changing state:

- Project Python runtime and package imports.
- PostgreSQL reachability from `DATABASE_URL`.
- Redis reachability from `REDIS_URL`.
- S3-compatible endpoint reachability from configured endpoint variables.
- Whether API/Web ports are already occupied.

Document native Windows commands for PostgreSQL/Redis/object-storage prerequisites, migrations, API, Celery worker/beat, and Web. Keep Docker Compose as an optional deployment path, not a local-development requirement.

### Step 3: Run the complete verification gate

Run:

```powershell
pnpm check
pnpm check:api-drift
pnpm --filter @gradmatch/web build
node scripts/native-status.mjs
```

If configured native services are available, also run migrations and exercise `/api/v1/health/ready`; otherwise report the specific unavailable dependency without claiming native readiness.

Perform a final requirements review against every global constraint, then request a code review before declaring completion.

Commit: `test: verify first pilot vertical slice`
