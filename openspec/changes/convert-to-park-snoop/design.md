## Context

The current repository contains the `integration_blueprint` custom component, no integration tests, and separate external BetterPark and ParkDepot/Wemolino investigation code. Existing workflows run Ruff, Hassfest, and HACS validation, but no tests. See `proposal.md` for the motivation and the change specifications for observable behavior.

## Goals / Non-Goals

**Goals:**

- Make provider-specific APIs independently replaceable behind a small typed contract.
- Keep all Home Assistant entity state in memory and update it from a single async monitoring runtime.
- Preserve provider evidence and uncertainty without collapsing concurrent sessions or misleading fee totals.
- Make provider additions discoverable and mechanically testable.

**Non-Goals:**

- Creating, changing, or paying for a parking session.
- Discovering arbitrary plates, scraping provider systems, or storing historical raw responses.
- Guaranteeing that a provider's display is legally authoritative or real-time.
- Supporting a multi-user/shared plate registry outside the Home Assistant configuration entry.

## Decisions

### One config entry, plate records in entry options, and plate devices

The integration will use one Park Snoop config entry and an options flow that manages a collection of plate records. Each record contains the normalized identifier, display metadata, cadence, and enabled provider identifiers. A plate's normalized identifier creates stable entity/device IDs; a rename therefore does not orphan history.

This keeps configuration user-facing and avoids configuration-YAML ownership problems. A config entry per plate would make bulk management and shared runtime scheduling awkward. Standalone entities without devices would lose the useful vehicle-level grouping requested by the user.

### Typed normalized domain model and provider registry

`models.py` will own immutable normalized types for results, sessions, fee values, outcomes, and session confidence. `providers/base.py` will define the abstract provider contract: immutable provider metadata, rate-limit policy, supported batching, and an async query that returns normalized results or typed provider errors. Concrete BetterPark and ParkDepot/Wemolino implementations will be the two initially registered providers.

Provider APIs must not dictate Home Assistant entities. Raw provider JSON remains local to the adapter and redacted diagnostics. A generic key/value API response or provider-specific entities was rejected because it makes extensions inconsistent and forces UI/automations to learn every provider schema.

### One runtime scheduler with a deduplicated priority queue

The config-entry runtime owns one cancellable asyncio scheduler task. It maintains a min-heap of due `(plate, provider)` jobs plus a key-indexed pending/running set. Jobs are coalesced by provider so batch-capable providers can receive multiple plate queries. The scheduler is the only component allowed to call providers; entities only render cached state and the manual button asks the scheduler to prioritize eligible work.

This replaces coordinator-wide fixed polling because each plate can have a different frequency and each provider can have a different limit. Dedicated threads were rejected: Home Assistant integrations are async, provider calls already use the shared aiohttp session, and threads complicate shutdown and state synchronization.

### Provider-owned limiter policies with central enforcement

Every provider declares a policy that calculates its next permitted request from observed requests, configured quotas, and cooldowns. The scheduler consults that policy before dispatch, then updates it after every response. A `Retry-After` response takes precedence. Without a usable provider retry time, rate-limited work is requeued no sooner than one minute. Transient failures use bounded exponential backoff plus jitter; schema/auth/permanent failures become surfaced provider errors rather than infinite retries.

Putting timing inside each provider would duplicate queue logic and permit inconsistent cancellation. A single global limit would be simpler but could throttle safe providers for the sake of a constrained one.

### Session aggregation preserves uncertainty and currency boundaries

The runtime indexes sessions by `(provider_id, provider_session_id)` and records whether a session is confirmed active, possibly active, closed, or unknown. Provider-specific closure rules determine when an absent response becomes a closure; a single absence never automatically produces a confirmed close. Plate aggregation derives the primary status and active-session count, including possible sessions for a `multiple_sessions`/`uncertain` presentation as specified.

Fees remain typed per session as amount, ISO currency, and meaning. Plate monetary entities sum only known active sessions in a single currency; unknown or other-currency amounts make the relevant total partial rather than misleading. A single cross-currency total was rejected as financially invalid.

### Entity design favors small, automation-ready entities

Each plate device exposes a primary enum-style status sensor, active-session count, per-currency monetary totals where applicable, last-check and next-check diagnostics, an optional binary parked indicator, and a button. A bounded `parking_details` representation contains only dynamic data that has meaning only in relation to the session list. Numeric or independently automatable information becomes its own entity instead of a large changing attribute.

### Test and documentation boundaries

Provider adapters will be unit tested with saved/sanitized payload fixtures; no CI job contacts live endpoints. Scheduler tests use a controllable clock and fake provider/limiter. HA tests use `pytest-homeassistant-custom-component`. The README serves normal users only, while `docs/adding_a_provider.md` and a disabled example provider explain extension work. Docstrings and comments document contracts and policy rationale, not syntax.

## Risks / Trade-offs

- [Provider APIs are public but undocumented, change, or restrict access] -> Isolate them in adapters, use conservative limits and contact identification when appropriate, surface failures, and keep tests fixture-based.
- [License plates, locations, and fees are sensitive] -> Store only needed configuration/current state, redact diagnostics/logs, and document privacy implications.
- [A provider lags after departure] -> Preserve a possibly-active state using explicit provider closure policy and show confidence in details.
- [Frequent entity attributes increase recorder size] -> Bound details, avoid raw responses, and use separate sensors for independently useful values.
- [Options-flow changes require runtime reconfiguration] -> Ensure scheduler jobs and platform entities are cleanly rebuilt with stable unique IDs and cancellation on unload.
- [A first-release provider exposes only EUR today] -> Model every monetary amount with ISO currency from the beginning, even when the UI initially most often creates EUR totals.

## Migration Plan

1. Replace the template domain and metadata with the Park Snoop domain before any platform is loaded.
2. Add configuration, provider runtime, entities, diagnostics, tests, documentation, and CI as one compatible custom-integration release.
3. The blueprint has no supported user configuration or historical data, so no user-data migration is required.
4. If rollout fails, uninstalling/removing the integration stops all runtime tasks; restoring the prior repository release restores the template state without a data transformation.

## Open Questions

- Provider endpoint behavior and published usage terms can evolve; the first implementation will encode only evidenced request formats and conservative limits, then adjust provider policy in later releases when authoritative provider guidance is available.
