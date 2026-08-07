# WML — GPT × Codex Shared Execution Layer

This repository is the shared execution and technical-memory layer between ChatGPT and Codex.

## Default principle

**Company Defaults by Default / Explicit Override**

- Unless the user explicitly overrides a rule for the current task, inherit the company-level defaults.
- If the user explicitly says a change should become the new default, update the shared rules before future execution.
- Project-specific rules override company defaults only within that project.

## Core files

- `AGENTS.md` — operating instructions for Codex and AI agents
- `PROJECT.md` — project scope and current technical context
- `BUSINESS_RULES.md` — stable business rules that implementation must preserve
- `ACCEPTANCE_CRITERIA.md` — definition of done and validation requirements
- `DECISIONS.md` — important technical/business decisions and rationale
- `CHANGELOG.md` — meaningful implementation changes

## Default workflow

1. User states business goal naturally in ChatGPT.
2. ChatGPT resolves relevant company/project context.
3. ChatGPT converts the goal into an executable task packet.
4. GitHub Issue stores the task, business rules, scope, and acceptance criteria.
5. Codex reads `AGENTS.md` plus the relevant project files before modifying code.
6. Codex implements and tests on a branch.
7. Pull Request records changes, tests, risks, and unresolved items.
8. ChatGPT reviews the PR from a business and acceptance-criteria perspective.
9. After approval/merge, durable decisions and reusable rules are written back to shared memory.

This repository should not become a dump of chat history. Store only durable rules, technical context, decisions, tasks, and implementation evidence.
