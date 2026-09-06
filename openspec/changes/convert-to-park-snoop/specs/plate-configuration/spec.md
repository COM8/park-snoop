## Purpose

Allow a Home Assistant user to configure the license plates and monitoring choices that Park Snoop manages without editing files.

## ADDED Requirements

### Requirement: Users can register and maintain monitored plates
The integration SHALL provide Home Assistant UI flows to add, edit, and remove registered license plates. A plate record MUST contain a normalized plate identifier and MAY contain a display name and private notes. A display name MUST be used in the UI when supplied; otherwise the normalized plate identifier MUST identify the plate. Removing a plate MUST stop its future checks and remove its Park Snoop entities.

#### Scenario: Adding a plate with defaults
- **WHEN** a user adds a valid plate without optional monitoring values
- **THEN** the plate is registered with a five-minute check frequency and every available provider selected

#### Scenario: Editing a plate
- **WHEN** a user changes a registered plate's display name, notes, frequency, or selected providers
- **THEN** later checks and displayed metadata use the saved values without changing the plate's stable entity identity

#### Scenario: Removing a plate
- **WHEN** a user removes a registered plate
- **THEN** the integration cancels its scheduled monitoring and removes the plate's integration entities

### Requirement: Plate configuration validates monitoring settings
The integration SHALL reject blank or invalid normalized plate identifiers, duplicate registered plate identifiers, check frequencies below one minute, and provider selections containing no available provider.

#### Scenario: Duplicate plate is rejected
- **WHEN** a user attempts to add a plate whose normalized identifier is already registered
- **THEN** the flow reports that the plate is already configured and does not create a duplicate

#### Scenario: Invalid frequency is rejected
- **WHEN** a user enters a check frequency below one minute
- **THEN** the flow reports a validation error and does not save the setting
