# ACCEPTANCE_CRITERIA.md

## Universal task acceptance checklist

Use this as the default definition-of-done layer unless a task defines stricter criteria.

- [ ] The requested user/business outcome is implemented.
- [ ] The implementation matches the current task scope.
- [ ] Documented business rules are preserved.
- [ ] Relevant existing behavior is not unintentionally removed.
- [ ] Relevant automated checks/tests pass where available.
- [ ] Necessary manual verification is documented where automation is insufficient.
- [ ] Error/edge states reasonably affected by the change were considered.
- [ ] The final diff was reviewed for unrelated changes.
- [ ] Risks, assumptions, and unresolved items are stated explicitly.
- [ ] The PR/task summary is understandable without rereading the full conversation.

## Task-specific acceptance criteria

Every GitHub implementation Issue should add concrete criteria under these headings when relevant:

### Functional
What must the user be able to do or observe?

### UX / Output
What must the interface, document, data, or response look like?

### Data / Business Rules
What rules must remain true?

### Validation
How will completion be verified?

### Non-goals
What should not be changed in this task?
