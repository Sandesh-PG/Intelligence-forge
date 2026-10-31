# Feature Specifications

Store one comprehensive Markdown specification per feature or tightly related implementation unit in this folder.

## Required workflow

1. Discuss the feature with the project owner.
2. Confirm dependencies and all decisions that affect data contracts, privacy, or architecture.
3. Write the feature spec before implementation.
4. Have the coding agent read `AGENTS.md`, all context files, and the complete active spec.
5. Implement only the active spec.
6. Verify every acceptance criterion.
7. Update `context/progress-tracker.md` and the spec status.

## Feature specification template

```markdown
# Feature NN: Feature Name

- Status: Draft | Approved | In Progress | Complete
- Owner:
- Dependencies:
- Related architecture decisions:

## 1. Goal
Describe the concrete user-visible or system-visible outcome.

## 2. User Story and Use Cases
Who uses it, what they need, and the supported scenarios.

## 3. Scope
### In scope
### Out of scope

## 4. Inputs and Outputs
Define request, file, event, and response contracts.

## 5. Detailed Workflow
Describe each processing step and decision branch.

## 6. Data Model
Define schemas, identifiers, relationships, indexes, and provenance.

## 7. Component Boundaries
Identify which services, repositories, adapters, APIs, and UI components own each responsibility.

## 8. Privacy and Security
Define trusted boundaries, sensitive data, allowed data flows, validation, and failure behavior.

## 9. Error and Edge Cases
Cover malformed input, empty results, provider failures, retries, partial failure, and duplicate operations.

## 10. UI/UX
Describe screens, states, interactions, accessibility, and responsive behavior.

## 11. Implementation Plan
Break work into ordered, verifiable subtasks.

## 12. Dependencies and Configuration
List packages, services, environment variables, and provider settings. Never include real secrets.

## 13. Acceptance Criteria
Use observable, testable checkboxes.

## 14. Test Plan
Unit, integration, end-to-end, security, and privacy tests.

## 15. Open Questions and Decisions
Record unresolved items. Do not silently assume answers.

## 16. Progress Log
Record meaningful implementation updates.
```

## Rules

- Do not write a feature spec that depends on unresolved architecture decisions without explicitly marking those dependencies.
- Do not copy the entire architecture into every feature spec; reference the relevant context documents and define only feature-specific detail.
- Privacy-sensitive features must include explicit outbound-data tests.
- A feature is not complete until its acceptance criteria are verified and the progress tracker is updated.
