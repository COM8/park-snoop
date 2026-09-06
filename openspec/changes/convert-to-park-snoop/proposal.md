## Why

The repository is an uncustomized Home Assistant integration blueprint and cannot monitor user-managed license plates across parking providers. Park Snoop will turn it into a reliable HACS integration that gives users timely, understandable parking-session and fee information while respecting provider limits.

## What Changes

- Replace the blueprint integration with the Park Snoop Home Assistant integration and HACS metadata.
- Let users manage license plates with an optional display name and notes, a check frequency defaulting to five minutes, and a selectable provider set defaulting to all available providers.
- Ship BetterPark and ParkDepot/Wemolino providers, normalize their different API results, and define a documented provider extension contract.
- Add a background scheduler with batched provider queries where supported, per-provider rate-limit policies, deduplicated jobs, and safe delayed retries.
- Represent every registered plate as a logical vehicle device with parking, active-session, fee, diagnostic, and manual-recheck entities.
- Distinguish confirmed, possibly active, closed, and unknown parking sessions; support concurrent sessions and currency-safe fee summaries.
- Add automated tests and CI quality gates aligned with current Home Assistant custom-integration and HACS expectations.
- Replace the template README with normal-user installation, setup, entity, privacy, and limitation guidance; publish separate provider-authoring documentation.

## Capabilities

### New Capabilities

- `plate-configuration`: Manage registered plates and their user-configurable monitoring settings.
- `provider-monitoring`: Query parking providers through a normalized, rate-limit-aware provider and scheduling framework.
- `parking-entities`: Expose each plate's aggregate parking state, sessions, monetary values, diagnostics, and manual refresh in Home Assistant.
- `integration-quality`: Deliver a HACS-ready integration with user documentation, provider-authoring guidance, tests, and continuous validation.

### Modified Capabilities

- None.

## Impact

- Replaces all files under `custom_components/integration_blueprint` with the Park Snoop domain and platforms.
- Updates HACS metadata, GitHub Actions, dependencies, scripts, tests, and repository documentation.
- Makes network requests to BetterPark and ParkDepot/Wemolino public-facing endpoints only through controlled provider implementations.
- Stores configured license plates and current monitoring state in Home Assistant; these are privacy-sensitive data and require redacted diagnostics/logging.
