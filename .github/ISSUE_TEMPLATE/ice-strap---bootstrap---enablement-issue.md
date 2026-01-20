---
name: ICE Strap — Bootstrap / Enablement Issue
about: >
  Bootstrap, packaging, and authority-boundary issues for ICE Strap.
  Covers determinism, scope drift, and strap → engine → runtime handoff.
title: "[STRAP-0X] "
labels: ["ice-strap", "bootstrap"]
assignees: []

---
## Type of Issue

Select **one**:

- [ ] Bootstrap determinism / reproducibility defect
- [ ] Scope drift (strap doing runtime/engine work)
- [ ] Authority handoff violation (strap → engine → runtime)
- [ ] Packaging / distribution issue (Python package, entry points, build)
- [ ] Documentation inconsistency / missing prerequisite
- [ ] Compatibility regression (OS, shell, CI, Python versions)
- [ ] Preboot isolation gap (checks / discovery / context)

Issues outside these categories may be closed.

---

## Context and References

Provide precise references.

- Project / Spec reference (required):
  - Project 2 item (e.g. **E-01.3**):
- STRAP phase (e.g. STRAP-04, STRAP-06):
- Repo area / path(s) involved:
- Related issue(s) / PR(s):
- CI / logs (if applicable):

---

## Problem Statement

Describe the problem **factually and precisely**.

- What fails or is ambiguous?
- What is the expected bootstrap behavior?
- What is the observed behavior?
- Is the issue deterministic?

Avoid opinions. Avoid solution proposals here.

---

## Environment

Fill what is relevant.

- OS / distro:
- Shell:
- Python version:
- Install method (pip / uv / source):
- Execution path (`python -m ice_strap`, CI, etc.):
- CI context (if any):

---

## Reproduction Steps

Provide minimal, reliable steps.

1.
2.
3.

Include exact commands.

---

## Constraint Alignment

Confirm alignment with ICE Strap constraints:

- [ ] No runtime or engine semantics introduced
- [ ] Authority boundaries preserved
- [ ] Bootstrap-only concern
- [ ] No changes to ice-runtime / ice-engine unless coordinated

---

## Definition of Done

Observable, verifiable criteria:

- Expected entry point(s):
- Expected bootstrap order:
- Expected authority handoff properties:
- Expected CI state:
