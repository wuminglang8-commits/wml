# BUSINESS_RULES.md

## Company-level execution defaults

### Rule 1 — Defaults are inherited

Unless the user explicitly overrides them, company-level standards and documented project rules remain active across future work.

### Rule 2 — Explicit override wins

A task-specific explicit instruction may override a default for that task. Do not automatically convert a one-off override into a permanent default.

### Rule 3 — Permanent changes must be persisted

When the user explicitly states that a new rule should apply going forward, update the relevant durable rule/document so both ChatGPT and Codex can inherit it.

### Rule 4 — Business intent before implementation convenience

Implementation must serve the business/user outcome. Do not simplify away behavior that matters commercially or operationally merely to make code easier.

### Rule 5 — No invented commercial logic

Do not invent or silently change:

- pricing;
- discounts;
- product eligibility;
- inventory relationships;
- probability/rarity rules;
- payment behavior;
- customer promises;
- partner rights/obligations;
- legal/compliance representations.

### Rule 6 — Acceptance must be observable

Every material task should define observable completion criteria. Prefer behavior, output, validation, and regression checks over vague statements such as “optimize” or “improve.”

## Document-system integration

Company document generation follows a separate Document Default System. Technical automation that generates business documents must not hard-code a single visual format for every audience. Audience/context determines the document route, and explicit user instructions override the default route.

## Future project rules

Project-specific business rules should be added under clearly named sections rather than mixed into company-level rules.
