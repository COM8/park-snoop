# Implementation handoff

## Local validation

Run on 2026-09-15 after the Park Snoop implementation changes:

| Command | Result |
| --- | --- |
| `python3 -m ruff format custom_components tests --check` | Passed: 31 files formatted |
| `python3 -m ruff check custom_components tests` | Passed |
| `env ANSIBLE_LOCAL_TEMP=/tmp/park-snoop-ansible python3 -m pytest -q` | Passed: 35 tests |
| `openspec validate convert-to-park-snoop --strict` | Passed |

## Hosted validation

Hassfest and HACS validation are provided by GitHub Actions
(`home-assistant/actions/hassfest` and `hacs/action`) rather than local command-line
tools. The validation workflow completed successfully for revision `9b5d324`,
including both checks: <https://github.com/COM8/park-snoop/actions/runs/35003411361>.
The offline test workflow also completed successfully:
<https://github.com/COM8/park-snoop/actions/runs/35003411723>.
