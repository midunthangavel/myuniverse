# Synapse AI — Phase 3 Implementation Plan

**Objective:** Turn the current Synapse prototype into a secure, dependable phone-native AI execution platform, then validate it with a small controlled pilot.

**Recommended strategy:** Secure and reconcile the source first; harden the four first-party capabilities and orchestration; prove end-to-end execution on the connected Android phone; then add selected integrations and pilot users. Do not spend Phase 3 building four polished app UIs. Keep the web simulator as a lightweight cockpit for conversation, approvals, traces, state inspection and demos.

## Current baseline and important caveat

The latest commit returned by the GitHub repository inspection was `8667bb1` on `main`. The remote source inspected still showed:

- a production-looking API-key value hardcoded in `src/agent.js`;
- `/api/showcase/run` and `/api/showcase/steps` excluded from API-key middleware;
- first-party REST endpoints that accept caller-supplied `tenant_id` values;
- first-party service data in `backend/app/first_party_services.py` stored in process-local dictionaries;
- a biometric approval handler that checks approval status and the server-issued transaction token but does not verify the Android-provided signature;
- no reported GitHub commit status checks for the inspected commit.

The latest local reports describe a durable capability/orchestration implementation and proactive briefing engine, but the corresponding orchestration and proactive-briefing routes/tests were not found on the inspected remote `main`. This may mean local work has not been pushed, is on another branch, or uses different filenames. **Reconcile the local and remote source before building on top of either version.**

## Phase 3 principles

1. **API-first for first-party services.** The AI invokes Calendar, Food, Messages and Tasks using typed capabilities. It should not need to click through its own services' UIs.
2. **UI automation for external apps only when needed.** Use supported APIs or native integrations first. Use the Android Accessibility/ADB path for third-party apps that do not expose an appropriate integration.
3. **Security before convenience.** No shared API secrets in browser code; no tenant chosen by an untrusted client; no sensitive action authorized by a client-supplied status flag.
4. **Truthful completion.** `DISPATCHED` is not `VERIFIED`. Every success claim must be backed by authoritative state or an external provider receipt.
5. **Durable, idempotent execution.** Retries and restarts must not duplicate messages, events, orders or payments.
6. **Ship by gates.** Do not proceed to the next stage until its acceptance criteria pass.

## Stage 0 — Source-of-truth and reproducibility

### Work
- Confirm the working branch, remote URL, latest commit and clean/dirty working tree.
- Find the local implementation described in the new reports; identify whether it is uncommitted, untracked, ignored or on another branch.
- Push the intended implementation to a named branch and merge it to `main` only after tests pass.
- Ensure `.env`, API keys, OAuth secrets, real user data, SQLite databases, browser recordings and private screenshots are not committed.
- Add a README section documenting local setup, environment variables, test commands, Android connection method and known demo-only behavior.
- Pin runtime versions and dependencies. Provide a safe `.env.example` with placeholder values that validation rejects as production secrets.

### Acceptance gate
- A clean checkout of the commit can be set up from the README.
- The intended orchestration, durable service and proactive-briefing source files are visibly present on the branch.
- No live credentials or private runtime artifacts are tracked.
- The exact commit SHA is recorded with test results.

## Stage 1 — Security and tenant boundary (P0 blocker)

### Work
- Rotate any real credential that has been exposed in source, reports, browser bundles or test fixtures. Remove shared API keys from `src/agent.js` and all browser-delivered JavaScript. A client must never possess a backend master secret.
- Replace the shared-key browser model with an appropriate authenticated session or short-lived, scoped client credential. Use TLS/WSS in deployed environments. Avoid long-lived tokens in WebSocket query strings; prefer a short-lived single-use connection ticket or a deliberate first-message authentication handshake.
- Keep unauthenticated access to a minimal health endpoint only. Protect showcase execution, governance, service mutations, task inspection and any endpoint with side effects. Make a state-changing showcase trigger `POST`, not `GET`.
- Derive tenant/user identity from the authenticated server-side principal. Do not accept `tenant_id` from the request body/query as the authority for data access. Reject attempts to act across tenants.
- Require enrolled, revocable device identities for device connections; remove development-token fallbacks from production paths.
- Add input validation, size limits, rate limits, structured errors, safe CORS origins and redaction of credentials/OTPs/tokens from logs.

### Acceptance tests
- Missing/invalid credentials are rejected on all protected routes.
- The browser bundle contains no shared backend secret.
- A valid user cannot read or mutate another tenant's rows by altering IDs or parameters.
- Public endpoints have no side effects.
- Revoked device credentials stop new connections and terminate existing sessions.

## Stage 2 — Durable service data and migrations

### Work
- Move Food, Messages, Calendar and Tasks away from in-process dictionaries into a shared repository/storage layer.
- Use explicit schemas, foreign keys, indexes, constraints, timestamps and migration scripts. SQLAlchemy plus Alembic is a reasonable approach if the current code has no existing migration framework.
- For local development and a single-process demo, SQLite can remain the first durable database. Before multi-worker or multi-instance cloud deployment, evaluate and normally move the shared primary store to PostgreSQL; do not assume file-backed SQLite is a horizontally scalable multi-user database.
- Create tenant-scoped persistent records for calendar events, food carts/orders, messages, tasks, execution runs/steps, idempotency keys, device enrollment and audit events.
- Use transactions for each state-changing capability. Add unique constraints for idempotency keys and provider event IDs.
- Store UTC timestamps and preserve the user's IANA time zone for calendar/date reasoning. Validate event overlap using intervals, not just identical start-time strings.
- Do not claim a message is `DELIVERED` or an order is externally placed when only a local row was written. Use honest lifecycle statuses such as `CREATED`, `QUEUED`, `SENT`, `DELIVERED`, `FAILED` or `SIMULATED`, as applicable.

### Acceptance tests
- Data survives backend restart and application reinitialization.
- Cross-tenant reads and writes fail.
- Concurrent retries do not create duplicate records.
- Calendar conflict detection catches partial overlaps and handles time zones.
- Food totals are computed on the server from trusted prices; quantity and priority values are validated.

## Stage 3 — Capability contract and orchestration engine

### Work
- Standardize each capability contract: name/version, validated input schema, required permissions, risk level, preconditions, idempotency key, timeout, result schema and verification method.
- Keep the first four capabilities focused: `calendar.create`/`calendar.reschedule`, `food.cart`/`food.order`, `message.send`, and `task.create`/`task.complete`. Add capabilities only when a real user workflow requires them.
- Make the orchestrator decompose compound intents into a dependency graph. Validate all required parameters and ask the user for missing information rather than inventing values.
- Show a plan/preview before irreversible or expensive actions. Obtain explicit approval before checkout, payment, external message dispatch or other high-impact operations.
- Persist task execution state and enforce legal transitions, for example: `CREATED → PLANNED → AWAITING_APPROVAL → RUNNING → SUCCEEDED/PARTIAL/FAILED/CANCELLED/EXPIRED`.
- Use a per-tenant idempotency key for each logical operation. Persist step results so an interrupted workflow resumes from the last safe checkpoint instead of repeating completed side effects.
- Support partial failure and compensation. Example: if Calendar creation succeeds but Food checkout fails, retain the calendar event, report the failed step and ask whether to cancel/reschedule; do not claim the compound task fully succeeded.
- Add request/task/step correlation IDs and bounded retries only for retry-safe operations.

### Acceptance tests
- A compound request generates the expected capability plan and validated arguments.
- Missing date/time/recipient/item details trigger clarification.
- Repeating the same request does not duplicate any committed side effect.
- Process restart during a workflow does not lose committed steps or silently rerun non-idempotent operations.
- Partial failures are reported accurately with per-step evidence.

## Stage 4 — Verification and financial authorization

### Work
- For first-party operations, verify from authoritative persisted rows by operation ID, tenant ID and final state.
- For third-party operations, verify provider responses/webhooks or a provider query; a local SQLite insert is not proof of external delivery.
- Keep `DISPATCHED`, `OBSERVED` and `VERIFIED` as distinct meanings. Never convert a client-reported dispatch into verified success without checking the outcome.
- Replace the current biometric trust model with a server-challenge protocol. Bind the challenge to tenant/device, task ID, exact action, amount, nonce and expiry. The Android app should use a device key protected by Android Keystore and gated by user authentication; the backend must verify the signature against the registered public key.
- Do not use the approval token itself as an HMAC key. Do not trust a client `APPROVED` status without cryptographic proof.
- Make single-use challenge consumption and approval state transitions atomic under concurrent requests. Enforce token expiry and action/amount binding.
- Make audit logging append-only at the application boundary, with access controls, integrity verification and an external/independent checkpoint for stronger tamper evidence. Do not describe SQLite alone as immutable or tamper-proof.

### Acceptance tests
- Invalid, expired, altered, wrong-tenant and replayed approvals are rejected.
- A client cannot authorize by sending only `status=APPROVED`.
- Concurrent approval attempts result in at most one successful authorization.
- Audit data contains no raw secrets and tamper checks detect modified records.

## Stage 5 — Real Android device validation

### Work
- Build and install the new Android APK on the connected Samsung Galaxy A26; record the exact APK/version and commit SHA.
- Verify device enrollment, authenticated WebSocket connection, permission states, Accessibility service enablement, reconnect and revocation.
- Keep first-party services on direct backend capabilities. Use UI/ADB automation only for third-party apps or device-native actions such as setting an actual alarm.
- For an external UI action, capture the precondition, command, post-action observation and expected semantic outcome. Confirm the correct foreground package and desired node/state before reporting completion.
- Remove hardcoded coordinate fallbacks. Prefer resource IDs, content descriptions, accessible text, dynamic node tree search and bounded scroll recovery. Coordinate-based gestures, where unavoidable, must be an explicit fallback with device/display calibration and still require outcome verification.
- Use `adb reverse`/localhost WebSocket only for controlled development. Document production routing and TLS separately.
- Record a short demonstration and structured run log, while ensuring screenshots and logs do not disclose private messages, tokens or personal data.

### Acceptance tests
- One alarm task is actually set and verified on device, not merely routed to the clock app.
- A representative third-party app workflow is completed and verified end to end.
- Screen changes, timeouts, app crashes, missing controls and network loss fail safely.
- No first-party capability requires opening its app UI to execute.

## Stage 6 — Proactive Morning Briefing and schedule optimizer

Implement or reconcile this feature only after the persistence and security stages are stable. The local report describes this engine, but its implementation must be present in the pushed branch before it can be treated as delivered.

### Work
- Read authorized calendar events and tasks, find interval overlaps, detect tight travel buffers using explicit/configurable assumptions, identify open lunch windows and prioritize due/high-priority tasks.
- Explain why each suggestion was generated and show confidence/assumptions where estimates are involved.
- Keep the briefing primarily read-only. Any reschedule, order or message action must go through the same capability contracts, tenant checks, idempotency and approval rules as normal requests.
- Schedule briefings by user time zone and preferences, honour quiet hours and provide an opt-out.
- Use a job queue/scheduler only with durable jobs, retries and duplicate suppression; do not create multiple background schedulers per API worker.

### Acceptance tests
- Briefing output is based on persistent current data and handles empty calendars, time zones and overlapping events.
- Recommendations do not execute merely because the briefing was viewed.
- Applying a recommendation is authenticated, idempotent and verified.

## Stage 7 — Voice interaction

### Work
- Add push-to-talk first: microphone permission, speech-to-text, intent decomposition, spoken response and streaming task status.
- Support interruption/cancellation and show the parsed plan before high-risk operations.
- Keep speech recognition and TTS failures independent from action execution: a TTS failure must not repeat an action.
- Do not treat voice recognition or a spoken phrase as sufficient financial authorization. Use the verified approval protocol above.
- Add wake-word/always-on listening only after explicit opt-in, clear privacy indicators and documented data retention.

### Acceptance tests
- The user can speak a compound request, review ambiguities, cancel safely and hear the actual result.
- Voice retries cannot duplicate an already dispatched operation.

## Stage 8 — External integrations (choose one at a time)

### Recommended sequence
1. Calendar ICS export and/or one approved Google Calendar OAuth integration.
2. One team notification provider, such as Slack or Discord webhook.
3. Real messaging/SMS through a supported provider, with consent, delivery status and applicable compliance handled.
4. A real food ordering/delivery provider only when an official supported integration is available.

### Work
- Store provider secrets server-side in environment/secret management.
- Use least-privilege OAuth scopes, encrypted tokens, refresh/revocation and per-tenant connection records.
- Use a transactional outbox, signed/validated webhooks, replay protection and provider event-ID deduplication.
- Separate `accepted`, `sent`, `delivered`, `failed` and `unknown` states. Never fake delivery receipts.
- Do not integrate all providers simultaneously; pick one workflow, validate it and then expand.

## Stage 9 — Observability, reliability and cost controls

### Work
- Measure end-to-end latency and each orchestration stage separately: planning, capability execution, provider wait, verification and user response.
- Capture p50/p95/p99, success rate, verification failure rate, partial failure rate, retries, idempotency conflicts, authorization denials, queue depth, provider latency and per-task cost.
- Use structured logs with correlation IDs and redaction. Never log raw API keys, HMAC/approval tokens, OTPs or unredacted sensitive messages.
- Set operational targets from baseline measurements rather than claiming sub-second completion based only on router classification time.
- Add timeouts, bounded retries, circuit breakers where appropriate, health/readiness probes, graceful shutdown and backup/restore verification.

## Stage 10 — CI/CD and security test automation

### Required automated checks
- Backend lint/type checks where configured and all unit/integration tests against temporary test databases.
- Frontend production build.
- Android Gradle assemble/build and static checks.
- Database migration tests from an empty database and the previous schema version.
- Security tests for auth bypasses, tenant isolation, revoked devices, replay, concurrent approvals, public side effects, secret leakage and oversized inputs.
- End-to-end orchestrator tests with injected provider failures and process restart.
- GitHub Actions on pull requests and pushes; merge only when required checks pass.
- Preserve raw test logs, test counts, skipped tests, environment and commit SHA as build artifacts.

## Stage 11 — Controlled pilot (after gates pass)

Do not start with a broad 5–50-user production rollout. Progress in tiers:

1. **Developer-only:** one account, local data, simulated providers.
2. **Internal alpha:** 3–5 explicitly consented users, real authentication, backups and support/rollback procedure.
3. **Small pilot:** increase cautiously after observing error rates, latency, recovery and support burden.
4. **5–50-user pilot:** only after tenant isolation, durable shared storage, monitoring, rate limits, provider limits, privacy review and incident response are validated.

### Cloud/runtime considerations
- Use a shared, durable database service rather than one SQLite file mounted ad hoc across horizontally scaled API instances.
- Add Redis/queues only when supported by a real need such as distributed coordination, durable job handling or connection management.
- Treat cloud Android runtime pooling as a separate capacity/cost project. First validate own-phone-first; do not add container pooling before measuring demand and isolation requirements.
- Define data retention, export/deletion, backup encryption, key rotation, abuse handling and a rollback/off switch for high-risk capabilities.

## Release gates

### Gate A — Source reproducibility
- New work is on GitHub and a clean checkout reproduces the test results.

### Gate B — Security baseline
- No browser master secret; server-derived tenant identity; protected mutation routes; cryptographically verified device approval; replay tests pass.

### Gate C — Durable core
- Four services persist across restarts, enforce tenant boundaries and support idempotent operations.

### Gate D — Reliable orchestration
- Compound requests, clarification, resumption, cancellation and partial failures are handled truthfully.

### Gate E — Device proof
- Physical Android end-to-end tests pass for native/device actions; first-party services use APIs, not UI taps.

### Gate F — Pilot readiness
- CI is green, monitoring and rollback work, backups are restored in a drill, privacy/data handling is documented and a limited-user pilot is approved.

## What not to prioritize yet

- Four polished first-party app viewports.
- A broad suite of model providers or elaborate analytics dashboards.
- Multi-user Android container pools before device-demand measurements.
- Always-on voice/wake-word before push-to-talk and privacy controls.
- Claims such as “zero flakiness,” “zero replay risk,” “tamper-proof,” or “production-ready” without explicit test evidence and a defined threat model.

## Immediate next actions

1. Reconcile local commits with `origin/main` and push the current orchestration/briefing implementation and tests, if they are the intended changes.
2. Rotate any real leaked credential and remove all shared secrets from frontend code and test/demo instructions.
3. Close the tenant-authorization, public showcase-route and biometric-verification gaps.
4. Persist the four service domains behind a repository layer and migrations.
5. Add CI and run tests on the exact commit.
6. Execute one end-to-end compound workflow on the real Android phone, using API capabilities for first-party operations.
7. Only then add one external integration and progress from internal alpha toward a multi-user pilot.

**Phase 3 definition of done:** Synapse can accept a compound request, build and execute a validated capability plan, request approval at the right boundary, persist and resume steps safely, verify actual outcomes, isolate users, recover from failure, and provide truthful results—reproducibly from the pushed commit and validated on the target phone. The number of UI screens is not a completion criterion.
