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
tools. The previously supplied GitHub Actions run was green; push the final commits
to run those hosted checks for the final revision.
