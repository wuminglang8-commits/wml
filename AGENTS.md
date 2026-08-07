# AGENTS.md — WML Shared AI Execution Standard

## 1. Mission

This repository is the shared execution layer between ChatGPT and Codex. Codex is the implementation engine; ChatGPT is normally the business-context, specification, orchestration, and acceptance layer.

The user should not need to restate the same business context in both systems.

## 2. Instruction precedence

Use this order when instructions conflict:

1. Explicit instruction for the current task
2. Current GitHub Issue / task acceptance criteria
3. Project-specific rules and documented decisions
4. `BUSINESS_RULES.md`
5. This `AGENTS.md`
6. Existing code conventions

Never silently override a higher-priority instruction.

## 3. Required pre-flight before implementation

Before changing code, read as applicable:

- `AGENTS.md`
- `PROJECT.md`
- `BUSINESS_RULES.md`
- `ACCEPTANCE_CRITERIA.md`
- relevant entries in `DECISIONS.md`
- the current GitHub Issue / task description
- the code paths directly affected by the task

Do not start with a broad rewrite before understanding the existing implementation.

## 4. Business-rule discipline

- Preserve documented business behavior unless the task explicitly changes it.
- Do not invent product, pricing, probability, inventory, UX, legal, payment, or operational rules.
- When requirements are ambiguous and the ambiguity could materially change business behavior, flag it rather than guessing.
- Prefer minimal, reversible changes over unnecessary architecture changes.
- Do not remove existing functionality merely because a simpler implementation is possible.

## 5. Implementation standard

For every implementation task:

1. Restate the goal in implementation terms.
2. Identify affected files/components.
3. Make the smallest coherent change that satisfies the goal.
4. Preserve compatibility unless explicitly told otherwise.
5. Run relevant tests/checks.
6. Inspect the resulting diff for unintended changes.
7. Report what changed, what was tested, known risks, and any unresolved decisions.

## 6. Definition of done

A task is not complete merely because code was written. It is complete only when:

- the requested behavior exists;
- acceptance criteria are satisfied;
- relevant tests/checks pass, or failures are explicitly documented;
- no obvious regression is introduced;
- business rules remain intact;
- the PR/task summary is understandable to a non-engineering decision maker.

## 7. Pull request standard

PR descriptions should contain:

### Goal
What business/user outcome this change serves.

### Changes
What was actually changed.

### Validation
Tests, checks, screenshots, or manual verification performed.

### Risks / Open Items
Known limitations, assumptions, migrations, or decisions still needed.

### Acceptance Criteria
A checklist mapped to the originating task.

## 8. Change-control rules

Explicit approval is required before:

- destructive data operations;
- changing payment or checkout logic;
- changing pricing or commercial rules;
- changing probability/randomization mechanics;
- changing authentication/security boundaries;
- deleting major existing functionality;
- broad architectural rewrites not required by the task.

## 9. Shared-memory hygiene

Do not write raw conversation history into this repository.

Persist only information that is useful across future tasks:

- stable business rules;
- project architecture/context;
- durable decisions and rationale;
- acceptance standards;
- meaningful implementation history.

If a new user instruction is explicitly declared to be a future default, update the relevant shared rule/document so future Codex work inherits it.

## 10. Communication style

Technical output should be precise and concise. Translate engineering details into business impact where useful. Surface uncertainty instead of hiding it.
