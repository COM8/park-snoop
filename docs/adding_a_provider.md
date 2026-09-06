# Adding a provider

Providers translate a parking service's public response into Park Snoop's
provider-neutral models. They must be independent: adding one cannot require
changing another adapter or a Home Assistant platform.

## 1. Start disabled

Copy `custom_components/park_snoop/providers/example.py` to a new module and
give its `ProviderMetadata` a stable, lowercase identifier. The example is
deliberately not registered, so it cannot be selected or queried. Do not add a
provider to the startup registry until its request, limits, normalization, and
tests are ready.

Set `supports_batching` to `True` only when the service supports one compatible
request for multiple plates. The scheduler uses that capability to choose
between grouped and one-plate queries.

## 2. Evidence and request safety

Document the public endpoint and its request shape near the adapter. Use the
shared Home Assistant `aiohttp` session, limit the request to configured
plates, and never retain raw response bodies. Do not use private endpoints,
credentials, or speculative request fields.

The adapter must declare and follow its own `RateLimitPolicy`. Its
`next_permitted_at` method prevents proactive over-requesting and
`record_request` is called after dispatch. Convert HTTP 429 into
`ProviderRateLimitError`, preserving only a numeric `Retry-After` delay when
available. Other transient and format failures use the typed provider errors;
the central scheduler decides bounded retry timing.

## 3. Normalize only the contract

Implement `async_query(plates)` and return exactly one `ProviderResult` for
each requested plate. A result holds the checked time, `ProviderOutcome`, and
zero or more `ParkingSession` values. Preserve only stable provider record IDs,
location, timestamps, fee currency and amount, fee meaning, and confirmation
state. Use `ProviderFormatError` for unexpected structures or GraphQL errors;
never expose a raw payload in an exception, entity, diagnostic, or log.

For unknown fee data, return no fee rather than guessing. Keep concurrent
sessions separate and use `normalize_plate` before matching a provider-returned
plate to the requested input.

## 4. Fixtures and tests

Save scrubbed representative responses under `tests/fixtures/`; fixtures must
not contain real plates, addresses, credentials, or personal data. Add offline
tests covering:

- a valid active parking response;
- an empty/no-parking response;
- malformed or provider-error responses;
- rate limiting, including a retry delay; and
- a batched multi-plate response when batching is supported.

Run `python3 -m ruff check custom_components tests`,
`python3 -m ruff format custom_components tests --check`, and
`python3 -m pytest -q` before registering the provider.

## 5. Register only after review

Create the implementation during integration setup and call
`ProviderRegistry.register`. Update the configuration choices and user-facing
documentation in the same change. Registration should be the only integration
change required for a completed provider; its request and conversion logic stay
inside its own module.
