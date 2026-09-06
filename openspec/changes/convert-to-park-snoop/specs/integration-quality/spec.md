## Purpose

Provide a dependable HACS installation experience with clear user guidance, repeatable provider contribution guidance, automated tests, and continuous validation.

## ADDED Requirements

### Requirement: HACS users receive clear installation and operating guidance
The repository README SHALL describe Park Snoop for normal Home Assistant users, including HACS installation from `COM8/park-snoop`, integration setup, plate monitoring behavior, available device entities, manual rechecks, fee limitations, and privacy considerations. It MUST NOT require users to understand provider implementation details.

#### Scenario: New user installs the integration
- **WHEN** a Home Assistant user follows the README
- **THEN** they can install Park Snoop through HACS, restart or reload as required, add the integration, and understand how to register a plate

### Requirement: Repository checks validate shipped behavior
The repository SHALL run formatting and lint checks, Home Assistant validation, HACS validation, and automated integration tests on pull requests and pushes to the default branch. Tests MUST cover configuration validation, normalized provider responses, scheduler rate-limit deferral, session/fee aggregation, and Home Assistant entities without making live provider requests.

#### Scenario: Regression is proposed
- **WHEN** a pull request breaks a covered provider, scheduler, configuration, or entity behavior
- **THEN** the continuous-integration test job fails before merge

### Requirement: Implementation documentation explains non-obvious behavior
Public integration and provider extension interfaces SHALL have Python docstrings, and code comments SHALL explain non-obvious policy, privacy, asynchronous scheduling, rate-limit, or provider-API decisions. The implementation MUST avoid comments that merely repeat self-evident code.

#### Scenario: Developer investigates a provider policy
- **WHEN** a developer reads a provider's rate-limit or result-normalization code
- **THEN** documentation explains the provider-specific assumption and why its policy is applied
