## 1. Project and test foundation

- [ ] 1.1 Rename the blueprint domain, manifest, translations, HACS metadata, and integration-facing names to Park Snoop, and verify Hassfest and HACS validation pass.
- [x] 1.2 Add the Home Assistant custom-component pytest dependencies and test configuration, and verify a minimal integration setup test runs without network access.
- [ ] 1.3 Replace or remove blueprint-only platforms, API client code, scripts, and template documentation, and verify no runtime reference to `integration_blueprint` remains with `rg`.

## 2. Domain model and plate configuration

- [x] 2.1 Implement typed, documented models for normalized plates, provider results, sessions, fee meaning, session confidence, and aggregate state, and verify unit tests cover concurrent sessions, unknown fees, and mixed currencies.
- [x] 2.2 Implement the initial config flow and options flow for adding, editing, and removing plates with display name, notes, frequency, and provider selection, and verify configuration-flow tests cover defaults and validation failures.
- [ ] 2.3 Implement stable plate-derived identifiers and safe runtime reconfiguration/removal, and verify a rename preserves entity IDs while removal unloads the plate's entities and scheduled work.

## 3. Provider framework and initial adapters

- [ ] 3.1 Implement the abstract provider contract, registry, typed errors, batching declaration, and provider-owned rate-limit policy interface with public docstrings, and verify a fake provider conforms in unit tests.
- [ ] 3.2 Implement the BetterPark adapter using the evidenced public plate-process endpoint and fixture-based response normalization, and verify tests cover active, empty, malformed, and rate-limited responses without live requests.
- [ ] 3.3 Implement the ParkDepot/Wemolino adapter using the evidenced open-orders GraphQL request and fixture-based normalization, and verify tests cover batched plates, empty orders, GraphQL errors, and rate limiting without live requests.
- [ ] 3.4 Add a disabled example provider and `docs/adding_a_provider.md` that document the complete extension flow, and verify the guide covers registration, rate limits, normalization, fixtures, and tests.

## 4. Scheduler, retry, and aggregation runtime

- [ ] 4.1 Implement one cancellable async config-entry scheduler with a deduplicated due-time queue and clean unload behavior, and verify scheduler tests prove no duplicate `(plate, provider)` job runs concurrently.
- [ ] 4.2 Implement provider query coalescing for batch-capable providers and individual dispatch for other providers, and verify fake-provider tests assert the expected request shape.
- [ ] 4.3 Implement central enforcement of provider-owned proactive limits, Retry-After cooldowns, one-minute fallback requeueing, and bounded transient retry backoff with jitter, and verify deterministic clock tests for each path.
- [ ] 4.4 Implement session lifecycle/closure policy and plate aggregation, including possibly-active sessions, `multiple_sessions`, currency-separated fee totals, and completeness indicators, and verify table-driven unit tests cover the specified scenarios.

## 5. Home Assistant entities and diagnostics

- [ ] 5.1 Implement a logical device and stable entities per plate for primary parking state, active-session count, parked indicator, per-currency fee totals, and last/next-check diagnostics, and verify Home Assistant entity tests assert state, device grouping, units, and unique IDs.
- [ ] 5.2 Implement the manual-recheck button as a scheduler request that remains subject to deduplication and provider limits, and verify an integration test covers button invocation during a pending job.
- [ ] 5.3 Add concise bounded session details, translated entity names/states, icon handling, and entity categories/default enablement consistent with Home Assistant guidance, and verify the integration tests do not expose raw provider payloads.
- [ ] 5.4 Implement redacted diagnostics and logging for plates, locations, and provider payloads, and verify tests prove default diagnostic output does not contain configured plate values or raw response bodies.

## 6. User documentation and continuous validation

- [ ] 6.1 Rewrite README.md for normal users with HACS installation from `COM8/park-snoop`, setup, entities, manual checks, fee semantics, limitations, and privacy guidance, and verify it contains no provider-authoring deep dive.
- [ ] 6.2 Update issue templates and contributor-facing references from the blueprint project to Park Snoop, and verify all repository links target `COM8/park-snoop` where applicable.
- [ ] 6.3 Add a GitHub Actions test job running the full offline test suite on pull requests and default-branch pushes while retaining Ruff, Hassfest, and HACS checks, and verify the workflow syntax and local test command succeed.
- [ ] 6.4 Run formatting, linting, all tests, Hassfest, HACS validation, and strict OpenSpec validation; fix all reported issues and record the final commands/results in the implementation handoff.
