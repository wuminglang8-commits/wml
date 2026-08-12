---
type: decision
status: active
source: chatgpt
updated: 2026-08-12
confidence: high
---

# Decision Index

## AI system decisions

### Company Defaults by Default / Explicit Override
Default company standards apply across ChatGPT and Codex unless the user explicitly overrides them for the current task. If the user says a change should apply going forward, persist it into shared memory.

### GitHub as canonical cross-tool source
GitHub `wml` is the shared knowledge/execution source for Codex and Obsidian. Obsidian should sync the same Markdown rather than become a separate unsynchronized knowledge base.

### Structured memory over raw chat dump
The default ChatGPT synchronization target is structured durable memory, project memory, decisions and important conversation summaries. Full raw chat export is optional archival material and should not be loaded by agents by default.

### Feishu knowledge discovery
Use controlled Business Knowledge Roots rather than assuming tenant-level global Drive enumeration. Knowledge roots may include Wiki spaces/subtrees, shared top-level Drive folders and known Bitable bases.

### Document Default System
Document format is routed by audience/use case. Formal government/school/corporate documents use restrained professional layouts; visual business PDFs and executive PPTs use stronger Canva-inspired visual communication.
