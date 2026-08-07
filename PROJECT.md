# PROJECT.md

## Purpose

WML is currently the company-level shared AI execution repository. Its first responsibility is to keep ChatGPT and Codex aligned on how technical work is specified, implemented, tested, reviewed, and remembered.

## Current phase

**Phase 1 — Shared execution foundation**

Current priorities:

1. Establish durable GPT ↔ GitHub ↔ Codex handoff rules.
2. Make natural-language business requests convertible into executable GitHub tasks.
3. Make Codex inherit stable project/business rules without repeated prompting.
4. Establish a consistent acceptance and PR-review loop.
5. Add project-specific technical context only when a real implementation project is attached to this layer.

## Repository role

This repository is currently a **shared control layer**, not yet a specific production application's source repository.

Future options:

- keep company-level standards here and link separate code repositories;
- or evolve this repository into a specific application repository if the user explicitly chooses that architecture.

Do not assume a production tech stack until it is documented here.

## Operating model

ChatGPT generally owns:

- business-context interpretation;
- requirement decomposition;
- research/strategy synthesis when needed;
- task specification;
- acceptance criteria;
- business-level PR review.

Codex generally owns:

- repository inspection;
- implementation planning at code level;
- code changes;
- tests/checks;
- technical validation;
- implementation notes.

GitHub owns the durable handoff:

- issues = executable task contracts;
- branches/commits = implementation history;
- PRs = review and acceptance surface;
- shared markdown files = durable technical/business memory.
