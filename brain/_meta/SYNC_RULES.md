# Sync Rules

## Canonical architecture

ChatGPT conversation/context → structured durable memory → GitHub `brain/` → Codex + Obsidian.

GitHub is the canonical cross-tool source. Obsidian should sync the repository rather than maintain a separate independent copy.

## ChatGPT write policy

Persist only when information is durable or the user explicitly asks to remember/synchronize it.

Preferred persisted forms:
- company fact
- project status
- business rule
- decision + rationale
- operating preference
- reusable workflow
- entity/partner context
- document/output standard

Do not automatically dump every conversation turn.

## Conversation memory layers

### Layer A — Durable Memory
Stable facts/defaults used across future tasks.

### Layer B — Project Memory
Project-specific goals, status, stakeholders, constraints and decisions.

### Layer C — Conversation Summaries
Structured summaries of important chat threads, linked to projects/entities.

### Layer D — Raw Archive (optional)
Full exported ChatGPT conversations, stored separately and not loaded by default.

## Codex read policy

Codex should:
1. read `brain/00_HOME.md`;
2. identify the current project/business entities;
3. read only relevant Company Brain notes;
4. prefer current Issue/task instructions over memory;
5. never treat unverified historical memory as a current external fact.

## Obsidian policy

Use Obsidian as the browsing/editing interface for the same Markdown repository. Prefer Obsidian links (`[[...]]`), YAML frontmatter, tags, backlinks and MOCs over duplicating files.

## Conflict policy

If Obsidian edits and ChatGPT/Codex edits conflict, resolve in Git. Newer text is not automatically authoritative; explicit user decisions and source-backed facts win.
