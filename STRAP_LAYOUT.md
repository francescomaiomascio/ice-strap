# STRAP-01 — Canonical Filesystem Layout (Frozen)

This document defines the canonical filesystem layout for the `ice-strap` repository.

This layout is the structural target of the refactor and is the reference gate for all subsequent STRAP sub-issues.

No code movement is performed in STRAP-01.
No logic changes are performed in STRAP-01.
No legacy deletion is performed in STRAP-01.

## Canonical Layout (Target)
```
ice-strap/
├── README.md
├── pyproject.toml
└── src/
    └── ice_strap/
        ├── __init__.py
        ├── __main__.py
        ├── bootstrap/
        │   ├── __init__.py
        │   ├── sequence.py
        │   ├── handoff.py
        │   └── errors.py
        ├── preboot/
        │   ├── __init__.py
        │   ├── checks.py
        │   ├── discovery.py
        │   ├── context.py
        │   └── ui.py
        ├── observability/
        │   ├── __init__.py
        │   └── init.py
        ├── config/
        │   ├── __init__.py
        │   └── defaults.py
        └── typing/
            └── protocols.py
```

## Responsibility Boundaries (Non-overlapping)

- ice_strap/__main__.py
  - single authoritative execution entry point for strap

- ice_strap/bootstrap/
  - ordering semantics and forward-only handoff
  - no runtime logic
  - no long-lived execution

- ice_strap/preboot/
  - system checks, discovery, bootstrap context construction
  - no runtime start

- ice_strap/observability/
  - preboot-only observability initialization (phase=preboot)
  - no runtime binding/rebinding

- ice_strap/config/
  - bootstrap defaults and parameter resolution
  - no runtime configuration

- ice_strap/typing/
  - contracts only
  - no wiring

## Forbidden Structures (Must Not Exist After Refactor)

- runtime/
- runtime_controller/
- system/runtime.py (or equivalent runtime stubs within strap)
- any long-lived execution loop inside strap
- any direct runtime start from strap
- any runtime-bound logging responsibilities inside strap
- any CLI decision logic that changes execution entry semantics

## Validation Gate

STRAP-01 is considered complete when:
- this document exists in the repository
- the target layout is unambiguous
- responsibility boundaries are explicitly stated
- forbidden structures are explicitly enumerated

Status: Frozen


## Responsibility Boundaries (Non-overlapping)

## STRAP-07 — Preboot Isolation Contract

The `preboot/` layer is a **pure preparation phase**.

It exists exclusively to **gather and validate facts**
required for bootstrap sequencing.

Preboot is executed **before** bootstrap
and **outside** any execution authority.

---

### Allowed Responsibilities (Preboot)

Preboot may perform **only**:

- filesystem checks
- environment validation
- permission inspection
- workspace discovery
- construction of an immutable `BootstrapContext`

Optional:
- diagnostic output
- non-interactive preboot UI
- human-readable validation feedback

---

### Forbidden Responsibilities (Preboot)

Preboot must **never**:

- start or control execution
- invoke engine or runtime
- make policy decisions
- transfer authority
- enforce ordering
- mutate filesystem state
- spawn processes
- perform network calls
- run loops or long-lived logic

If any of the above occurs, preboot is **invalid**.

---

### Authority and Semantics

- Preboot owns **no authority**
- Preboot does **not decide**
- Preboot does **not execute**
- Preboot does **not persist**

Preboot outputs exactly one artifact:


This artifact is:
- immutable
- passed forward exactly once
- consumed by bootstrap
- never modified by preboot after creation

---

### Relationship to Bootstrap

- Preboot gathers facts
- Bootstrap enforces order
- Authority transfer happens **after preboot**
- Preboot cannot influence sequencing
