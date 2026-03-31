<!--
  Sync Impact Report
  ==================
  Version change: N/A (template) → 1.0.0
  Modified principles:
    - [PRINCIPLE_1_NAME] → I. Code Quality
    - [PRINCIPLE_2_NAME] → II. Testing Standards
    - [PRINCIPLE_3_NAME] → III. User Experience Consistency
    - [PRINCIPLE_4_NAME] → IV. Performance Requirements
    - [PRINCIPLE_5_NAME] → REMOVED (not needed; user requested 4 principles)
  Added sections:
    - Quality Gates (was [SECTION_2_NAME])
    - Development Workflow (was [SECTION_3_NAME])
    - Governance (filled from [GOVERNANCE_RULES])
  Removed sections:
    - Principle 5 slot removed (template had 5; user specified 4)
  Templates requiring updates:
    - .specify/templates/plan-template.md ✅ no update needed
      (Constitution Check section is already generic/dynamic)
    - .specify/templates/spec-template.md ✅ no update needed
      (Requirements and success criteria sections already align)
    - .specify/templates/tasks-template.md ✅ no update needed
      (Task phases and test-first guidance already compatible)
    - .specify/templates/checklist-template.md ✅ no update needed
      (Generic template; categories filled dynamically)
    - .opencode/command/*.md ✅ no update needed
      (No agent-specific names found; constitution references are
       path-based and remain valid)
  Follow-up TODOs: None
-->

# MySkills Constitution

## Core Principles

### I. Code Quality

All code committed to the repository MUST meet the following standards:

- **Readability**: Code MUST be self-documenting. Functions, variables,
  and types MUST use descriptive names that convey intent. Comments
  MUST explain "why," not "what."
- **Single Responsibility**: Every module, class, and function MUST
  have a single, well-defined responsibility. If a unit requires
  more than one sentence to describe its purpose, it MUST be split.
- **Consistent Style**: A project-wide linter and formatter MUST be
  configured and enforced. No code MUST be merged that fails lint
  or format checks.
- **No Dead Code**: Unused imports, unreachable branches, and
  commented-out code MUST be removed before merge.
- **Error Handling**: All error paths MUST be explicitly handled.
  Silent failures (swallowed exceptions, ignored return values)
  are prohibited.

**Rationale**: Maintainability degrades exponentially with code
quality shortcuts. Enforcing quality at the source prevents
compounding technical debt.

### II. Testing Standards

Testing is a mandatory gate for all functional changes:

- **Coverage Minimum**: Every feature MUST include tests that cover
  its acceptance scenarios. Untested code MUST NOT be merged.
- **Test Pyramid**: Unit tests MUST form the base. Integration tests
  MUST cover cross-boundary interactions. End-to-end tests SHOULD
  be used sparingly for critical user journeys only.
- **Test Independence**: Each test MUST be independently runnable
  and MUST NOT depend on execution order or shared mutable state.
- **Determinism**: Tests MUST produce the same result on every run.
  Flaky tests MUST be quarantined and fixed within one sprint or
  removed.
- **Descriptive Naming**: Test names MUST describe the scenario and
  expected outcome (e.g., `it returns 404 when user not found`).

**Rationale**: Tests are the executable specification of the system.
Without disciplined testing, regressions accumulate and confidence
in deployments erodes.

### III. User Experience Consistency

All user-facing interfaces MUST deliver a coherent, predictable
experience:

- **Design System Adherence**: UI components MUST use the project's
  established design tokens (colors, spacing, typography). Ad-hoc
  styling is prohibited for any element that has a design-system
  equivalent.
- **Interaction Patterns**: Navigation, form behavior, error display,
  and loading states MUST follow documented UX patterns. Deviations
  MUST be approved and documented before implementation.
- **Accessibility**: All interactive elements MUST meet WCAG 2.1 AA
  compliance. Semantic HTML, ARIA attributes, and keyboard
  navigation MUST be verified.
- **Feedback & State Communication**: Every user action MUST produce
  visible feedback (loading indicators, success confirmations,
  error messages). The system MUST NOT leave the user uncertain
  about the outcome of an action.
- **Responsive Behavior**: Interfaces MUST function correctly across
  all supported viewport sizes and input methods.

**Rationale**: Inconsistent UX erodes user trust and increases
support burden. A unified experience reduces cognitive load and
training costs.

### IV. Performance Requirements

All features MUST meet performance thresholds before release:

- **Response Time**: User-facing operations MUST complete within
  200ms at the 95th percentile under expected load. Operations
  exceeding 1 second MUST display a progress indicator.
- **Resource Efficiency**: Memory allocations MUST be profiled for
  features handling large data sets. Unbounded growth (memory
  leaks, cache bloat) is prohibited.
- **Bundle Size**: Frontend assets MUST NOT exceed established
  budgets. New dependencies MUST be evaluated for size impact
  and tree-shakability before adoption.
- **Startup Time**: Application cold-start MUST remain within
  documented thresholds. Lazy loading MUST be used for non-critical
  modules.
- **Monitoring**: Performance-sensitive paths MUST include
  instrumentation (timing metrics, resource counters) that is
  observable in production.

**Rationale**: Performance is a feature. Users abandon slow
applications, and degradation is difficult to reverse once
architectural decisions are entrenched.

## Quality Gates

All changes MUST pass the following gates before merge:

1. **Lint & Format**: Automated style checks MUST pass with zero
   violations.
2. **Test Suite**: The full test suite MUST pass. No failing or
   skipped tests are permitted on the main branch.
3. **Code Review**: At least one reviewer other than the author
   MUST approve the change. Reviewers MUST verify alignment with
   all four constitutional principles.
4. **Performance Check**: Changes to performance-sensitive paths
   MUST include benchmark results demonstrating no regression.
5. **Accessibility Audit**: UI changes MUST include an accessibility
   review (automated tooling at minimum; manual audit for complex
   interactions).
6. **Constitution Compliance**: The reviewer MUST confirm that no
   constitutional principle is violated. Violations MUST be
   resolved or escalated before merge.

## Development Workflow

1. **Branch Strategy**: All work MUST occur on feature branches.
   Direct commits to the main branch are prohibited.
2. **Specification First**: Features MUST have an approved spec
   before implementation begins. The spec MUST reference which
   constitutional principles apply.
3. **Incremental Delivery**: Work MUST be broken into independently
   testable increments aligned with user stories. Each increment
   MUST be deployable without breaking existing functionality.
4. **Continuous Integration**: Every push MUST trigger the full
   quality gate pipeline. Broken builds MUST be fixed before any
   new work is merged.
5. **Documentation**: Public APIs, configuration options, and
   architectural decisions MUST be documented at the time of
   implementation, not deferred.

## Governance

This constitution is the authoritative source for project standards.
All other guidelines, templates, and processes MUST align with it.

- **Amendments**: Any change to this constitution MUST be proposed
  in writing, reviewed by at least one project maintainer, and
  include a migration plan for existing code that conflicts with
  the new rule. Amendments MUST NOT be made implicitly through
  practice drift.
- **Versioning**: This constitution follows semantic versioning:
  - MAJOR: Principle removed, redefined, or made incompatible
    with prior interpretation.
  - MINOR: New principle or section added, or existing guidance
    materially expanded.
  - PATCH: Clarifications, typo fixes, non-semantic refinements.
- **Compliance Review**: At the start of each feature plan, the
  Constitution Check section MUST be completed to verify alignment.
  Violations discovered during implementation MUST be logged and
  resolved before the feature is considered complete.
- **Precedence**: In case of conflict between this constitution and
  any other project document, the constitution takes precedence.

**Version**: 1.0.0 | **Ratified**: 2026-03-31 | **Last Amended**: 2026-03-31
