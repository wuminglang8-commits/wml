# DECISIONS.md

Record durable decisions here. Do not record routine implementation details.

## 2026-08-07 — Use GitHub as GPT ↔ Codex durable handoff layer

**Decision:** Use GitHub Issues, repository guidance, commits, and PRs as the durable execution bridge between ChatGPT and Codex.

**Why:** Chat context and Codex execution context should not depend on manual copy/paste or repeated explanations. GitHub provides an auditable shared layer.

**Implication:** Important implementation tasks should be converted into explicit task contracts with acceptance criteria before Codex execution.

## 2026-08-07 — Company Defaults by Default / Explicit Override

**Decision:** Stable company/project rules are inherited automatically unless explicitly overridden for a task.

**Why:** Reduce repeated prompting while keeping the user's current instruction authoritative.

**Implication:** One-off overrides do not become permanent defaults unless the user explicitly says they should apply going forward.

## 2026-08-11 — Inventory Feishu through controlled Knowledge Roots

**Decision:** A tenant application inventories only explicitly configured Wiki spaces/subtrees, shared Drive folders, and Bitable Bases. It does not infer workspace-wide coverage from tenant Wiki/Drive roots.

**Why:** Feishu tenant applications do not have an enterprise-wide personal Drive root, and accessible Wiki spaces depend on explicit membership and permissions. Global enumeration therefore cannot reliably represent the business workspace.

**Implication:** Inventory reports always state the configured-root coverage boundary, preserve partial failures, and require deliberate root configuration before live scans.

## 2026-08-07 — Separate orchestration from implementation

**Decision:** ChatGPT normally handles business interpretation, task decomposition, and business acceptance; Codex normally handles code implementation and technical validation.

**Why:** This reduces context duplication and lets each surface specialize while sharing GitHub as the contract and evidence layer.
