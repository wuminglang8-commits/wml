# AGENTS.md — WML Shared AI Execution Standard

## 1. Mission

This repository is the shared execution and knowledge layer between ChatGPT, Codex, and Obsidian. Codex is the implementation engine; ChatGPT is normally the business-context, specification, orchestration, memory-curation, and acceptance layer. Obsidian is the human-facing knowledge interface over the same Markdown source.

The user should not need to restate the same business context in different systems.

## 2. Instruction precedence

Use this order when instructions conflict:

1. Explicit instruction for the current task
2. Current GitHub Issue / task acceptance criteria
3. Project-specific rules and documented decisions
4. Relevant notes under `brain/`
5. `BUSINESS_RULES.md`
6. This `AGENTS.md`
7. Existing code conventions

Never silently override a higher-priority instruction.

## 3. Required pre-flight before implementation

Before changing code, read as applicable:

- `AGENTS.md`
- `brain/00_HOME.md`
- relevant notes linked from the Company Brain Home
- `PROJECT.md`
- `BUSINESS_RULES.md`
- `ACCEPTANCE_CRITERIA.md`
- relevant entries in `DECISIONS.md`
- the current GitHub Issue / task description
- the code paths directly affected by the task

Do not load the entire Company Brain indiscriminately. Resolve the current project/entities first and read only relevant notes.

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

The canonical cross-tool business-memory directory is `brain/`.

Do not automatically write raw conversation history into the operational memory layer. Persist structured information that is useful across future tasks:

- stable business rules;
- company context;
- project architecture/status;
- durable decisions and rationale;
- acceptance standards;
- entity/partner context;
- reusable workflows;
- important conversation summaries;
- document/output standards.

Full raw ChatGPT exports, if intentionally imported, belong in a separate archive layer and should not be loaded by default.

If a new user instruction is explicitly declared to be a future default, update the relevant Company Brain note so future ChatGPT/Codex work inherits it.

## 10. Communication style

Technical output should be precise and concise. Translate engineering details into business impact where useful. Surface uncertainty instead of hiding it.

For the current user, technical instructions should default to beginner-friendly execution: ask the user to perform only actions that require personal authorization, credential entry, or a simple one-line command; Codex should handle the rest where possible.
