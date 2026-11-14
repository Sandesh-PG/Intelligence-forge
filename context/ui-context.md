# UI Context — Intelligence Forge

## 1. Product Experience Principles

The interface is a research workspace. It should be:

- Research-oriented and focused.
- Clear when presenting complex information.
- Trustworthy, with visible source attribution.
- Transparent about whether an answer came from the private knowledge base or web fallback.
- Calm and readable during document processing and long-running operations.

Avoid decorative complexity that competes with research content, unexplained AI-generated claims, hidden loading/error states, and presenting web-derived information as if it came from uploaded papers.

## 2. Core UI Areas

### Research workspace
- Main area for asking questions and reading answers.
- Clear indication of the active knowledge-base/workspace context.
- Conversation or query history only if included in the approved feature scope.

### Document ingestion
- File selection/drop area for supported papers.
- File validation feedback.
- Per-document processing status.
- Summary and extraction status where supported.
- Clear retry/error messaging without exposing secrets or raw provider payloads.

### Answer presentation
- Structured answer with headings, paragraphs, lists, or tables as appropriate.
- Source/provenance references for KB-derived claims where available.
- Explicit source-path label such as `Knowledge Base` or `Web Search`.
- External web citations/links when available.
- Distinguish missing evidence, conflicting evidence, and provider errors.

### Privacy feedback
- Explain when a question is answered from the private knowledge base.
- If web fallback is used, indicate that a privacy-reviewed query was sent externally.
- Do not expose raw private retrieval payloads or sensitive internal sanitization details.
- If a query cannot be safely sent, clearly state that external search was not performed.

## 3. Visual Design Status

The visual system is **deferred**, not a blocker for backend setup or early functional work.

Before detailed UI implementation, decide:
- Light/dark theme or supported theme modes.
- Color palette and semantic design tokens.
- Typography.
- Component library, if any.
- Icon library, if any.
- Navigation and workspace layout.
- Responsive behavior for the screens in scope.

Do not fill in arbitrary design-token values before the team makes these decisions. When a UI feature is ready to be designed, propose a small number of coherent options and record the approved choice here.

## 4. Accessibility and UI Behavior

- Use semantic buttons, labels, headings, lists, and form controls.
- Ensure keyboard access and visible focus states.
- Provide accessible names for icon-only controls.
- Do not rely on color alone to communicate source path, status, or errors.
- Include loading, empty, success, warning, partial, and error states where applicable.
- Preserve readable contrast and responsive behavior.
- Use reusable components for source labels, document status, evidence references, and answer sections when appropriate.

## 5. UI Acceptance Principles

A UI feature is not complete unless:
- Its applicable loading, empty, success, and error states are handled.
- It clearly communicates whether information is KB-derived or web-derived.
- It does not expose private document contents unintentionally.
- It is keyboard-operable and has accessible labels.
- It follows the visual decisions approved for that feature.
- It is usable at the responsive sizes specified in its feature spec.
