---
name: ICE Strap — Bootstrap / Enablement Issue
about: 'Bootstrap/packaging issues for ICE Strap: determinism, scope-drift, and strap
  → engine → runtime handoff.'
title: ''
labels: ''
assignees: ''

---

## Type of Issue

Select **one**:

- [ ] Bootstrap determinism / reproducibility defect
- [ ] Scope drift (strap doing runtime/engine work)
- [ ] Authority handoff violation (strap → engine → runtime)
- [ ] Packaging / distribution issue (Python package, entry points, build)
- [ ] Documentation inconsistency / missing prerequisite
- [ ] Compatibility regression (OS, shell, CI, Python versions)
- [ ] Observability preboot gap (phase=preboot)

Issues outside these categories may be closed.

---

## Context and References

Provide precise references.

- Project / Spec reference (required):  
  - Project 2 item (e.g., E-01.3):  
- Repo area / path(s) involved:  
- Related issue(s) / PR(s):  
- Logs / CI links (if applicable):  

---

## Problem Statement

Describe the problem **factually and precisely**.

- What fails or is ambiguous?
- What is the expected bootstrap outcome?
- What is the observed outcome?
- Is the issue deterministic or intermittent?

Avoid opinions. Avoid solution proposals at this stage.

---

## Environment

Fill in what is relevant.

- OS / distro:  
- Shell:  
- Python version:  
- Installation method (pip/uv/poetry/source):  
- Execution path (module, script, entry point):  
- CI context (if any):  

---

## Reproduction Steps

Provide minimal, reliable steps.

1.
2.
3.

Include exact commands when possible.

---

## Evidence

Attach objective evidence.

- Error output / stack trace:
- Relevant snippets (small, focused):
- Screenshots (if UI/CI):
- Notes on frequency / determinism:

---

## Constraint Alignment

Confirm alignment with ICE Strap constraints:

- [ ] This does not introduce new runtime/engine semantics
- [ ] This preserves upstream authority (Foundation / Project 2 semantics)
- [ ] This is a bootstrap/enablement concern (not a product feature)
- [ ] This does not request changes to ice-runtime or ice-engine (unless explicitly coordinated)

---

## Proposed Direction (Optional)

If you propose a direction, it must be:

- scoped to strap (bootstrap, packaging, preboot)
- semantically neutral (no new execution model)
- explicit about how it preserves Project 2 constraints

Leave empty if not applicable.

---

## Definition of Done (Optional)

If relevant, state acceptance criteria in observable terms.

- Expected entry point(s):
- Expected bootstrap order:
- Expected handoff properties:
- Expected artifacts (packages, files, logs):
- Expected CI checks:
