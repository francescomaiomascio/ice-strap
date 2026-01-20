## Context

Closes #<ISSUE_NUMBER>

This PR addresses **STRAP-0X** by implementing a strictly scoped,
bootstrap-only change aligned with Project 2 constraints.

---

## What Changed

Describe **only what actually changed**.

- Files added / modified:
- Responsibilities introduced or removed:
- Boundaries enforced (sequence, authority, scope):

---

## What Did NOT Change

Explicitly state what is untouched:

- No runtime lifecycle logic
- No engine semantics
- No authority beyond strap scope
- No long-lived processes

---

## Validation

Demonstrate correctness.

- [ ] `import ice_strap` succeeds
- [ ] `python -m ice_strap` behaves as expected
- [ ] Guardrails pass
- [ ] CI checks green

Include commands or output if useful.

---

## Architectural Confirmation

Confirm the following:

- [ ] Bootstrap sequence remains linear and forward-only
- [ ] Strap exits after handoff
- [ ] No strap → runtime calls
- [ ] Preboot remains isolated

---

## Notes (Optional)

Anything worth preserving for future phases.
