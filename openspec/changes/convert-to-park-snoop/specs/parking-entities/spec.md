## Purpose

Expose one understandable Home Assistant vehicle device per monitored plate while preserving evidence for simultaneous and uncertain parking sessions.

## ADDED Requirements

### Requirement: Each plate has a stable logical device and core entities
The integration SHALL create one logical device for every registered plate using a stable plate-derived identity. Each device MUST expose parking status, active-session count, a manual recheck button, and last-check diagnostics. The primary state MUST be one of `not_parked`, `parking`, `multiple_sessions`, `uncertain`, `unknown`, `rate_limited`, or `error`.

#### Scenario: Single confirmed session
- **WHEN** exactly one provider reports a confirmed active session for a plate
- **THEN** the device's primary parking status is `parking` and its active-session count is one

#### Scenario: Simultaneous sessions
- **WHEN** two or more providers or records report confirmed or possibly active sessions for a plate
- **THEN** the device's primary parking status is `multiple_sessions` and the active-session count reflects every included session

#### Scenario: Manual recheck
- **WHEN** a user presses the plate device's manual recheck button
- **THEN** the integration requests an eligible immediate check for every selected provider while continuing to enforce provider limits

### Requirement: Session confidence avoids false closures
The integration SHALL distinguish confirmed active sessions from possibly active sessions when provider data is delayed, stale, incomplete, or temporarily unavailable. It MUST not represent an unconfirmed absence as a confirmed closed session. Device details MUST identify the provider and confidence of every active or possibly active session.

#### Scenario: Provider has not yet reflected a departure
- **WHEN** a previously active provider session has not been conclusively closed but is absent from a later provider response
- **THEN** the device retains it as possibly active until the provider-specific closure policy considers it closed

### Requirement: Fee representation is currency-safe and semantically clear
The integration SHALL retain fee meaning per session as an accrued estimate, amount due, final charge, or unknown. It MUST only aggregate known active-session fees with the same ISO 4217 currency and MUST expose the aggregate's fee completeness. It MUST NOT sum values across currencies or label an estimate as a payable amount.

#### Scenario: Known EUR fees from active sessions
- **WHEN** active sessions report known EUR fee values
- **THEN** the device exposes their EUR total as a monetary sensor and identifies whether every active session contributed a known fee

#### Scenario: Mixed currencies
- **WHEN** active sessions report fee values in more than one currency
- **THEN** the device exposes separate currency-specific totals or session details and does not expose a cross-currency sum

#### Scenario: Provider does not provide a fee
- **WHEN** an active session has no provider fee information
- **THEN** the device presents the session as fee-unknown and marks any relevant aggregate as incomplete

### Requirement: Sensitive details and diagnostics are bounded
The integration SHALL expose concise, current session details needed to understand the plate state, without persisting raw provider payloads in entity state. Diagnostics and logs MUST redact license plates and provider payload data unless a user explicitly enables appropriate debug logging.

#### Scenario: Provider response contains unrelated data
- **WHEN** a provider response includes raw fields not required for the normalized session view
- **THEN** those fields are not placed in Home Assistant entity attributes
