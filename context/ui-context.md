# UI Context — Intelligence Forge

## 1. Design Status

**Visual design is not finalized.** The product is a research workspace, but the project team has not yet approved a light/dark theme, color palette, typography, component library, or layout system.

Until the team approves a visual direction:
- Do not invent a complete brand identity or apply arbitrary colors.
- Inspect the existing repository and preserve any established UI conventions.
- Build accessible, functional layouts with semantic HTML and reusable components.
- Keep design tokens centralized so the visual system can be changed consistently.
- Record proposed design choices as proposals, not approved decisions.

## 2. Product Experience Principles

The interface should feel:
- Research-oriented and focused.
- Clear when handling complex information.
- Trustworthy, with visible source attribution.
- Transparent about whether an answer came from the private knowledge base or web fallback.
- Calm and readable during document processing and long-running operations.

Avoid:
- Decorative complexity that competes with research content.
- Unexplained AI-generated claims.
- Hiding loading, error, or insufficient-evidence states.
- Presenting web-derived information as if it came from uploaded papers.

## 3. Core Screens and UI Areas

### Research workspace
- Main area for asking questions and reading answers.
- Clear indication of the current knowledge-base/workspace context.
- Conversation or query history only if included in the approved scope.

### Document ingestion
- File selection/drop area for supported research papers.
- File validation feedback.
- Per-document processing state: queued, processing, completed, or failed (final state names may be refined in the feature spec).
- Summary and extraction status where supported.
- Clear retry/error messaging without exposing internal secrets or raw provider payloads.

### Answer presentation
- Structured answer with readable headings, paragraphs, lists, or tables as appropriate.
- Source/provenance references for KB-derived claims where available.
- Explicit source-path label: `Knowledge Base` or `Web Search`.
- External web citations/links when available.
- Distinguish missing evidence, conflicting evidence, and provider errors.

### Privacy feedback
- Explain when a question is being answered from the private knowledge base.
- If web fallback is used, indicate that a sanitized query was sent externally.
- Do not expose the raw private retrieval payload or internal sanitization rules in a way that leaks sensitive information.
- If the query cannot be safely sanitized, show a clear message that external search was not performed.

## 4. Design Tokens

The following are semantic token names only. Values must be chosen and approved by the project team before final styling.

| Role | CSS variable | Approved value |
|---|---|---|
| Page background | `--color-bg` | TBD |
| Main surface | `--color-surface` | TBD |
| Elevated surface | `--color-surface-elevated` | TBD |
| Primary text | `--color-text` | TBD |
| Secondary text | `--color-text-muted` | TBD |
| Primary accent | `--color-accent` | TBD |
| Border | `--color-border` | TBD |
| Success | `--color-success` | TBD |
| Warning | `--color-warning` | TBD |
| Error | `--color-error` | TBD |
| Focus ring | `--color-focus` | TBD |

Do not hardcode color values inside individual feature components once tokens are established.

## 5. Typography and Shape

| Element | Decision |
|---|---|
| UI font | TBD |
| Heading scale | TBD |
| Body text scale | TBD |
| Metadata/small text | TBD |
| Monospace font | TBD |
| Small control radius | TBD |
| Card/panel radius | TBD |
| Dialog radius | TBD |

Prioritize readable body text, clear heading hierarchy, and comfortable line length for long research answers.

## 6. Component and Accessibility Conventions

- Component library: TBD.
- Icon library: TBD.
- Use semantic buttons, labels, headings, lists, and form controls.
- Ensure keyboard access and visible focus states.
- Provide accessible names for icon-only controls.
- Do not rely on color alone to communicate source path, status, or errors.
- Include loading, empty, success, warning, partial, and error states.
- Preserve readable contrast and responsive behavior.
- Use reusable components for source badges, document status, evidence references, and answer sections when appropriate.

## 7. Layout Patterns

These are functional requirements, not a finalized wireframe:

- **Workspace:** a focused research area with document context and question-answer interaction.
- **Upload area:** a clear upload affordance with supported-format guidance and processing status.
- **Answer view:** readable content with source-path identification and citations.
- **Evidence/source view:** expandable or linked source details where available.
- **Responsive behavior:** core upload and Q&A flows must remain usable on common desktop and mobile widths.

Exact navigation, sidebar behavior, panel widths, and mobile layout are TBD and must be decided before detailed UI implementation.

## 8. UI Acceptance Principles

A UI feature is not complete unless:
- Its loading, empty, success, and error states are handled where applicable.
- It clearly communicates whether information is KB-derived or web-derived.
- It does not expose private document contents unintentionally.
- It is keyboard-operable and has accessible labels.
- It follows the approved tokens and component conventions.
- It is usable at the responsive sizes required by its feature spec.
