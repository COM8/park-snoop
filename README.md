# Park Snoop

Park Snoop is a Home Assistant custom integration that monitors configured
license plates with supported parking providers. It is read-only: it never
starts, changes, or pays for parking.

## Install with HACS

1. In HACS, open **Integrations** and select **Custom repositories**.
2. Add `COM8/park-snoop` as an **Integration** repository.
3. Search for **Park Snoop**, install it, then restart Home Assistant.
4. Go to **Settings → Devices & services → Add integration**, select **Park
   Snoop**, and finish the initial setup.

## Add a plate

Open the Park Snoop integration's **Configure** action to add, edit, or remove
plates. Each plate has an optional display name and notes, a check interval
(five minutes by default), and one or more parking providers. Removing a plate
stops its future checks and removes its Park Snoop entities.

## Entities and manual checks

Each plate is represented as one Home Assistant device. Its entities show the
current parking status, active-session count, whether it is parked, per-currency
fee totals when known, and last/next-check diagnostics. Use its **Recheck**
button to request an immediate eligible check. Provider cooldowns and limits
still apply, so a manual request may wait briefly rather than overload a
provider.

Fees are provider-supplied estimates, amounts due, or final charges as labelled
by the provider. Park Snoop never sums different currencies and marks totals as
incomplete when a provider does not report a fee.

## Limitations and privacy

Provider data can be delayed, incomplete, or change without notice. Treat Park
Snoop as an informational aid, not a legally authoritative parking record.
Configured plates, current parking locations, and fees can be sensitive. The
integration stores only the configuration and current normalized state needed to
monitor them; diagnostics and normal logs redact plate values and provider
payloads.

For contribution guidance, see [CONTRIBUTING.md](CONTRIBUTING.md).
