# GradMatch architecture baseline

**Version 1.3 | Updated 2026-09-01**

## Purpose and boundaries

GradMatch starts as a Web-first modular monolith. `apps/web` owns the Next.js presentation layer; `services/api` owns Django business persistence, authentication, administration, API contracts, and background ingestion. This is intentionally not a microservice system.

`packages/domain` contains platform-neutral rules and query definitions. `packages/design-tokens` contains semantic design values only. `packages/api-client` is generated from Django Ninja and allauth OpenAPI specifications; browser, Web server, and the future Expo app consume these clients instead of copying DTOs.

## Browser and API path

The browser has one Caddy origin. `/api/*`, `/_allauth/*`, `/accounts/*`, `/admin/*`, `/static/*`, and `/media/*` go to Django. All other paths go to Next.js. Browser requests stay relative to this origin so Django can use Secure, HttpOnly, SameSite cookies without CORS configuration. Server Components use `GRADMATCH_API_BASE_URL` to call the internal API service.

Authentication is Django allauth Headless. Browsers use session cookies; a future mobile app uses allauth `X-Session-Token`, not JWT. Email verification is mandatory, and the product currently supports password plus one-time-email-code login. Phone, WeChat, and QQ are extension boundaries only.

Every browser client that can call a state-changing Django endpoint uses the same CSRF-token and retry middleware; this is not limited to allauth calls. Public liveness exposes only a coarse status. Dependency readiness, environment, build and model/provider details are restricted to internal operations paths and never rendered on public pages.

## Background data boundary

Celery worker and beat share the Django codebase and Redis broker. The current fixture adapter and `RawArtifact` model are foundation code, not the production evidence contract. Before any real source is connected, migrate to `RawBlob` for content-addressed bytes and `SourceFetch` for every access attempt (source, URL, request/fetch time, status, ETag/Last-Modified, blob and run). Two identical fetches therefore create two fetch records and one blob. Evidence records use `PROTECT` or additive invalidation rather than cascading deletion.

Object writes and database publication use a recoverable protocol: stage object, verify hash, commit references and an outbox event, then finalize/garbage-collect idempotently. Fetchers enforce allowlisted hosts, post-DNS private/metadata-address blocking, redirect revalidation, response size/MIME/time limits and real rate limiting. Source access is enabled only after rights, terms, display scope and takedown ownership are recorded.

## MVP domain boundaries

The existing `system`, `accounts`, and `ingestion` modules are the implemented foundation. The product PRD adds the following modules inside the same Django monolith; these are module boundaries, not deployable services:

- `catalog`: coverage manifests, taxonomy revisions/nodes/mappings, institutions, schools, programs, annual offerings, plan observations, exam bundles, cost profiles, source revisions, evidence claims, reviews and publication workflow.
- `advising`: confirmed study goals and versioned user facts, hard constraints, preference-factor definitions, rule-set revisions, eligibility checks, comparison runs/groups, decision snapshots, optional recommendation explanations, usage links and action items.
- `outcomes`: metric definitions, structured evidence scopes, career-outcome evidence, occupations, qualifications, program-to-occupation links, and scope-compatibility decisions.
- `llm_gateway`: provider adapters, structured-output validation, evidence binding, cost/time budgets, audit metadata, and safe fallback.
- `support`: correction cases, complaints, review queues, publication events, immutable audit events, and user-visible case status.
- `commerce`: product offers, orders, payments/refunds, entitlements, and commercial experiments. This boundary remains disabled for real payments until the strategy Go/No-Go prerequisites are met.
- `governance`: capability-scoped gate decisions and deployment fingerprints. It does not decide product facts; it prevents external research, sources, AI, public deployment, payment, or advertising from activating without a current exact-scope decision.

`catalog` publishes versioned admissions evidence. `outcomes` publishes versioned career evidence and scope decisions without mutating `catalog`. `advising` is the only module allowed to calculate the three eligibility states and four comparison groups. `llm_gateway` may explain an `advising` result but cannot create or override facts, rules, eligibility states, ranking inputs, career metrics, or scope decisions. `support` can propose changes but only the relevant publication workflow can make evidence current. `commerce` may grant access to product capabilities but cannot write catalog facts, outcome facts, eligibility, natural ordering, or recommendation reasons. `governance` is checked at capability activation and deployment startup; a feature flag cannot bypass it.

PostgreSQL remains the source of truth and is sufficient for the pilot's structured search, rules, version history, transactional outbox and audit indexes. Celery handles ingestion, revalidation, affected-plan recomputation, exports, deletion, and notifications through `JobExecution` plus idempotency keys. Object storage holds isolated immutable source blobs and separately derived/redacted display artifacts. Redis is transient and cannot be the only copy of a product fact, event or job outcome. No vector database, external search service, event bus, or microservice split is required for the MVP.

## Decision and evidence model

The catalog hierarchy is versioned and variable rather than forced through one fixed chain:

`CoverageManifest -> TaxonomyRevision -> TaxonomyNode(parent, level_type, code) -> AnnualOffering`

An annual offering may attach to an official first-level discipline, degree category, professional field or institution-specific node. `TaxonomyMapping` records old/new nodes, `mapped / ambiguous / unmapped / institution_specific`, effective dates, confidence and evidence. Historical offerings retain the taxonomy revision under which they were published. A 2025 correspondence must not overwrite an older code or imply identical training content.

The minimum annual-offering decision records are:

- `PlanObservation`: original reported value, optional derived value, plan stage, pathway, study mode, special/joint scope, numerator/denominator text, evidence and status. Components may overlap or be unpublished, so the database does not enforce that they sum to the published total or silently derives unified-exam places.
- `ExamSubjectBundle`: subject code/name, national or institution-set status, applicability, and change events. A separate comparability decision prevents scores from incompatible bundles from being ranked together.
- `ProgramCostProfile`: duration, per-year/total tuition, accommodation availability/cost, scholarship eligibility, campus, target year, and evidence status. User-entered living and opportunity costs remain in `advising`, not in shared catalog facts.
- `StudyGoal`, `PreferenceFactorDefinition`, and `PreferenceProfile`: confirmed goals plus versioned factor meaning, allowed evidence, scope, unknown handling and explanation templates. Up-to-three factors totaling 100 is one P1 experiment; it is never required for a safe result and historical survey percentages never populate it.
- `SubjectMigrationAssessment`: known matching subjects, new requirements, unknowns, extra tests, and source-bound reasoning. It does not calculate admission probability.

Null means unknown throughout these records. Zero is used only when an official source explicitly states zero for the same scope.

The evidence graph is many-to-many and revisioned:

`SourceDocumentRevision -> EvidenceClaimRevision -> ReviewDecision -> PublicationEvent`

`RuleEvidenceUsage`, `ComparisonRuleUsage`, and `ComparisonEvidenceUsage` bind published claims to `RuleSetRevision`, `EligibilityCheck`, `ComparisonRun`, and `DecisionSnapshot`. Optional AI explanations use separate `RecommendationRuleUsage` and `RecommendationEvidenceUsage` records referencing an immutable comparison run. A rule set includes an applicability/coverage manifest; `eligible_known` is possible only when that manifest is complete and every applicable check passes. Any unknown rule, applicability, user fact or source conflict becomes `needs_confirmation`; any known applicable failure becomes `ineligible_known`.

`DecisionSnapshot` has a required outcome enum: `shortlist_ready`, `no_suitable_offering`, `awaiting_official_information`, or `postpone_application`. It records retained, excluded and deferred candidates, user-confirmed reasons, key unknowns with reason codes, next actions, revisit date, `comparison_run_id`, fact/rule/evidence versions and a deterministic result hash. It stores no scalar confidence or admission probability; each rendered field carries its evidence status. Replaying the same deterministic inputs must reproduce eligibility, grouping and order. Optional LLM prose is not regenerated to prove equality; the original response, prompt-template version, input snapshot and validation result are retained.

Guest comparison runs and snapshots use a random, short-lived, resource-scoped capability token delivered to the browser as a Secure, HttpOnly, SameSite cookie; only its hash is persisted. `POST /decision-snapshots/{id}/claim` requires both an authenticated session and the valid guest capability, then atomically assigns ownership and rotates/revokes the guest token. IDs alone never authorize reads or claims.

## Career outcome scope

Career evidence is not an attribute column on `Program`. It uses three explicit records:

- `MetricDefinition`: stable key and version, numerator/denominator definitions, statistic (`rate`, `mean`, `median`, `p25`, `p75`), unit, currency basis, observation window, and inclusion/exclusion rules.
- `EvidenceScope`: education level, degree type, study mode, taxonomy revision/code, institution/school/program, cohort year, time since graduation, region, industry, sample size, response rate, and source grade.
- `CareerOutcomeEvidence`: metric value, definition, scope, source document/claim, review status, and optional uncertainty metadata.

The `outcomes` compatibility service stores independent `entity_match`, `population_match`, `time_match`, `metric_match`, and `mode_match` decisions, then returns the aggregate `exact_match`, `broader_context`, or `incompatible` plus rule version and reasons. Only an aggregate `exact_match` may be labeled as direct historical program evidence. `broader_context` is display-only context and never enters natural ordering. `incompatible` is excluded from program and comparison APIs.

Required guards include: undergraduate outcomes cannot become master's outcomes; industry-wide wages cannot become graduate starting salaries; institution-wide rates cannot become program rates; ungrouped or differently defined academic/professional and full-/part-time samples cannot compare those groups; same-source, same-cohort, consistently defined and adequately grouped samples may compare; means and medians are not interchangeable. Metric-definition or scope-rule changes enqueue affected-result recomputation while preserving the previous decision for audit.

`Occupation` uses the national occupation classification where available. `ProfessionalQualification` records entry versus level-evaluation status and evidence. Stability, work intensity, income volatility, geographic concentration, relevance, and further-study opportunity remain separate observations; there is no `social_status_score` field.

## Commercial isolation

The first software commercial hypothesis is a target-year or application-season decision package, not a permanent subscription assumption. `commerce` owns `ProductOffer`, `Order`, `PaymentRecord`, `Refund`, `Entitlement`, and `CommercialExperiment`. Real payment providers stay disabled until entity, merchant payment, order, service/refund, reconciliation, invoicing, filing/licensing, and privacy prerequisites pass the strategy gate.

Entitlements may control deep-comparison limits, saved-plan capacity, evidence-update alerts, or collaboration. They cannot be inputs to catalog publication, evidence grading, outcome scope, eligibility, natural ordering, or recommendation reasons. The advising API never receives payment amount, sponsor identity, or commission as a ranking feature.

The free entitlement always permits one safe decision loop: eligibility, conclusion-changing facts and unknowns, official sources, base comparison, a decision snapshot, and S0/S1 correction or eligibility-invalidation notices. Paid offers add cross-time convenience, history, monitoring, collaboration, export depth or SLA; they never unlock hidden truth. Commercial relationships also cannot change inclusion, update priority, evidence placement or correction priority.

Manual diagnostic services and software packages have separate offer IDs and ledgers. A cohort records received revenue, refunds, payment fees, direct review/support, model/notification cost, paid acquisition, preregistered key application-node events and D30 proxy events. Data-operations work logs record entry, independent review, rework, change and support time. Reports expose delivery contribution, after-attributable-acquisition contribution, annual operating profit after allocated fixed people/compliance/infrastructure cost, and 12-month monthly cash flow. A profitability gate requires annual aggregate after-acquisition contribution to exceed allocated fixed cost; revenue alone is not the numerator. Expansion also checks the current six-month committed-spend liquidity policy. Activation cost is not paid CAC; software profitability is not inferred from manual-service revenue.

Payment remains disabled until an offer has a versioned entitlement matrix, delivery boundary, interruption compensation, refund triggers, responsibility allocation, merchant/order/reconciliation/invoicing readiness and applicable consumer/advertising review. `PaymentAttempt`, `Refund`, `EntitlementAdjustment`, and `ExperimentExposure` use idempotency keys and auditable state transitions.

## Local development and deployment shape

The first product implementation slice deliberately excludes LLM, payment and mobile UI. It uses the three planned annual-offering IDs frozen in [pilot scope V1](research/pilot-scope-2027-v1.md), with every unpublished 2027 fact explicitly pending, to prove:

`source fetch -> raw blob -> evidence claim -> independent review -> publication -> user fact revision -> eligibility check -> comparison -> decision snapshot -> correction -> new publication -> idempotent recomputation -> user-visible diff`

Before the applicable 2027 rule manifest is published and independently reviewed, production eligibility for these planned identities can only be `needs_confirmation`. Automated coverage of `eligible_known` and `ineligible_known` uses a non-production fixture namespace with either synthetic rules or historical snapshots carrying `reference_year=2026`; fixtures are rejected by production serializers and never count toward manifest coverage or user conclusions.

The minimum API surface is `GET /pilot-scope`, `GET /taxonomy`, `GET /offerings`, `GET /offerings/{id}`, `POST /fact-sets`, `POST /eligibility-assessments`, `POST /comparison-runs`, `GET /comparison-runs/{id}`, `POST /decision-snapshots`, `GET /decision-snapshots/{id}`, `POST /decision-snapshots/{id}/claim`, `POST /corrections`, and `GET /corrections/{id}`. A comparison run deterministically calculates eligibility, grouping and order; a snapshot selects one outcome and freezes user decisions against that run. Invitation begins only after the same contract passes against [the frozen ten-offering manifest](research/pilot-scope-2027-v1.md).

AI endpoints, UI and provider calls are feature-disabled for the first invitation. The AI requirements become blocking only before that capability is enabled, at which point structured evidence binding, all fallback drills, labels/complaints and a matching `GateDecision` must pass together.

Local development does not require Docker. Web, Django, Celery worker/beat, PostgreSQL, a Redis-compatible broker, S3-compatible object storage, and local mail capture run as native processes or installed local services. Workspace scripts should start application processes and perform dependency checks without moving persistent data back to the C drive. Tests continue to use isolated test settings and local fixtures.

Docker Compose remains an optional reproducible single-host packaging target for CI or a future server, not a prerequisite for local feature development. In that packaging mode PostgreSQL, Redis, MinIO, and Mailpit are internal dependencies; a one-shot migration service is the only process that runs migrations and collects static assets. Kubernetes, vendor-specific deployment services, GraphQL, and external search are explicit non-goals.

## Pilot operational budgets

These are invitation-pilot budgets, not claims about a later nationwide service:

- Search, detail, and comparison APIs target a 95th-percentile server time of at most 750 ms under 30 concurrent pilot users, excluding external document fetches and LLM calls.
- Evidence-backed pages must remain usable without JavaScript for core reading; interactive changes show progress within 100 ms and a useful result or explicit pending state within 2 seconds under the pilot dataset.
- An LLM request has an 8-second soft timeout and a 15-second hard timeout. At the hard timeout the UI follows the verified-data fallback instead of waiting indefinitely.
- PostgreSQL and object snapshots receive a daily recoverable backup. The invitation pilot targets RPO 24 hours and RTO 4 hours; one restore drill is required before public launch.
- Admin roles are `viewer`, `editor`, `reviewer`, and `administrator`. Publishing P0 evidence requires an explicit review action distinct from extraction/editing; all publication, rule, correction, export, and deletion actions are audited.
- Audit records exclude raw conversation text and secrets and are access controlled. Network logs, business audit, behavior analytics, conversations, orders and evidence artifacts each have purpose-specific retention; applicable statutory minimums override the pilot default, and longer retention requires documented necessity.
- Health and dependency details remain available to internal monitoring only. Public errors use sanitized categories and an opaque event ID.

Performance acceptance uses a fixed dataset, endpoint mix, request bodies, cache state, duration and scoring script; “30 concurrent users” alone is not reproducible evidence. Before inviting users, one PostgreSQL plus object-snapshot restore drill must meet the stated RPO/RTO.

## External release gates

Capabilities are independently gated:

- external research: notice/consent, withdrawal and compensation, de-identification, retention and access control;
- production sources: rights/display basis, terms/robots, crawler security, redaction and takedown;
- external AI: provider/processor/subprocessor, region, retention/training use, automated-decision assessment, explicit/implicit labels and applicable filing/registration determination;
- public Web or app: entity/domain/deployment-specific filing or licensing, security classification/protection applicability, privacy rights and incident response;
- payment or advertising: merchant, order/contract, delivery/refund, reconciliation/invoicing, consumer protection, ad labeling/copy and testimonial review.

Each gate releases only the named capability. An 18+ product scope does not redefine statutory child/minor rules. Linkable account/session identifiers are treated as de-identified personal information, not anonymous data. These controls require deployment-specific professional determination and do not assert that every listed filing applies to every architecture.

Every result is an immutable `GateDecision(state, capability, scope, deployment_fingerprint, approver, evidence_ref, decided_at, expires_at, conditions, supersedes_id)`. `state` is one of `pending`, `go`, `conditional_go`, `not_applicable_with_rationale`, or `no_go`. Activation is allowed only for the exact capability and fingerprint when the current decision is `go`, when all recorded conditions of `conditional_go` have been verified, or when a signed `not_applicable_with_rationale` supports non-applicability. Pending, no-go, expired, unmet-condition, or fingerprint-changing deployments are blocked by default.

## Mobile migration path

No Expo UI is built yet. When it is, Expo/React Native consumes `packages/domain`, `packages/design-tokens`, and `packages/api-client`; platform-specific components remain in the mobile app. This keeps future Android and iOS work from duplicating request types, validation rules, or product semantics.
