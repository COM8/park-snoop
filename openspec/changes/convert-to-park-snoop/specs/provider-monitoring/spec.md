## Purpose

Monitor configured plates through BetterPark, ParkDepot/Wemolino, and future providers while giving each provider safe control over its requests and results.

## ADDED Requirements

### Requirement: Initial providers return normalized parking results
The integration SHALL query BetterPark and ParkDepot/Wemolino for every due plate that selected that provider. It MUST convert provider responses into a provider-neutral result containing the queried plate, check time, outcome, and zero or more parking sessions. A session MUST retain its provider identity, provider record identity when available, location, times, fee amount and currency when available, fee meaning, and confirmation state.

#### Scenario: BetterPark reports an active process
- **WHEN** BetterPark returns an active parking process for a due plate
- **THEN** the normalized result contains an active session associated with BetterPark and the provider's available location, time, and fee information

#### Scenario: ParkDepot/Wemolino reports no order
- **WHEN** ParkDepot/Wemolino returns no applicable open order for a due plate
- **THEN** the normalized result records a successful no-parking outcome for that provider

### Requirement: Providers are extensible and documented
The integration SHALL define a documented provider contract for declaring provider identity, supported query shape, rate-limit policy, request implementation, and normalized-result conversion. The repository MUST include a complete, non-enabled example and an authoring guide that demonstrate adding a provider without modifying unrelated provider implementations.

#### Scenario: Adding an independent provider
- **WHEN** a developer follows the provider authoring guide to add a provider that conforms to the contract
- **THEN** that provider can be selected for a plate and its results participate in the common monitoring and entity behavior

### Requirement: Due checks are scheduled safely
The integration SHALL schedule each selected plate-provider pair when its configured frequency is due, prevent duplicate pending work for the same pair, and allow a manual refresh to make it eligible immediately. Providers that support batched lookups MUST receive compatible due plates in batches; providers that do not MUST receive individual lookups.

#### Scenario: Concurrent normal and manual request
- **WHEN** a user requests a manual refresh while the same plate-provider check is already pending or running
- **THEN** the integration does not create duplicate provider work and publishes the result of the existing or next eligible check

#### Scenario: Batch-capable provider has multiple due plates
- **WHEN** multiple due plates use a provider that supports batched lookup
- **THEN** the provider receives one compatible batched query rather than one query per plate

### Requirement: Provider limits and failures delay rather than overload requests
The integration SHALL apply each provider's declared rate-limit policy before sending a request. On a provider cooldown, expected limit, or rate-limit response, it MUST defer affected work until the provider's indicated retry time or at least one minute later when no retry time is supplied. Transient communication failures MUST use bounded delayed retries, and permanent/provider-format failures MUST be surfaced without an unbounded retry loop.

#### Scenario: Proactive rate limit delay
- **WHEN** a due request would exceed a provider's declared limit
- **THEN** the worker requeues the request for the provider's next permitted time without sending it

#### Scenario: Rate-limit response with Retry-After
- **WHEN** a provider responds with a rate-limit status and a Retry-After value
- **THEN** the integration delays affected provider work until no earlier than that value

#### Scenario: Rate-limit response without retry time
- **WHEN** a provider signals rate limiting without a usable retry time
- **THEN** the integration requeues the work at least one minute later
