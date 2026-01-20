# ICE Strap

> **The canonical bootstrap layer of the ICE ecosystem**  
> Bringing ICE systems into existence — correctly, deterministically, and once.

---

## What is ICE Strap

ICE Strap is the **bootstrap and provisioning layer** of the ICE ecosystem.

It is responsible for initializing ICE systems **before any execution,
intelligence, or runtime behavior exists**.

ICE Strap defines **how ICE starts** — and nothing more.

Once control is handed off to the Engine or Runtime,
ICE Strap **permanently exits**.

---

## Why ICE Strap Exists

Most system failures are born at startup.

Modern systems often:
- mix initialization with execution
- hide authority handoff
- perform irreversible actions too early
- blur responsibility boundaries

ICE Strap exists to make system startup:

- explicit
- deterministic
- inspectable
- auditable

It answers one foundational question:

> **How does an ICE system come into existence correctly?**

---

## Core Responsibilities

ICE Strap is responsible for:

- providing a **single authoritative entry point**
- performing **preboot validation**
- discovering environment and workspace context
- creating an **immutable bootstrap context**
- enforcing a **canonical bootstrap sequence**
- handing off authority exactly once
- exiting permanently after handoff

ICE Strap is intentionally small.
Every line of code is part of system birth.

---

## Canonical Bootstrap Sequence

ICE Strap enforces a **strict, forward-only sequence**:

1. Strap starts (`python -m ice_strap`)
2. Preboot checks
3. Environment & workspace discovery
4. Bootstrap context creation (immutable)
5. Topology decision (local / remote / engine target)
6. Engine bootstrap invoked
7. Authority handed off
8. Strap exits permanently

Any deviation from this order is invalid by design.

---

## What ICE Strap Is Not

ICE Strap **does not**:

- run workloads
- manage lifecycles
- orchestrate agents
- execute runtime logic
- retry execution
- host control loops
- remain alive after startup

ICE Strap is not a runtime.
It is not an orchestrator.
It is not a controller.

It is a **bootstrap boundary**.

---

## Authority Model

ICE Strap exercises **transitional authority only**.

It may:
- validate preconditions
- refuse invalid startup
- establish initial structure
- transfer authority forward

It may **not**:
- authorize execution
- retain control after handoff
- call runtime directly
- bypass governance rules

Authority flows strictly forward:

**Strap → Engine → Runtime**

Never backward. Never in parallel.

---

## Position in the ICE Ecosystem

ICE Strap is one domain in a modular system:

- **ICE Foundation**  
  Defines axioms, invariants, and non-negotiable rules.

- **ICE Strap**  
  Brings the system into existence.

- **ICE Engine**  
  Performs reasoning and decision-making.

- **ICE Runtime**  
  Executes and orchestrates system behavior.

ICE Strap precedes all execution layers.

---

## Design Constraints (Non-Negotiable)

The following are **forbidden** in ICE Strap:

- runtime execution
- subprocess runtime launch
- long-lived loops
- lifecycle management
- retry semantics
- runtime-bound logging
- implicit authority transitions

These constraints are enforced structurally and through CI guardrails.

---

## Project Status

ICE Strap is under **active development**.

- APIs are intentionally minimal
- semantics are conservative
- breaking changes are rare but high-impact
- correctness is prioritized over convenience

ICE Strap evolves slower than downstream systems — by design.

---

## Contributing

Contributions are welcome, but constrained.

Before contributing:
- understand the canonical bootstrap sequence
- respect forward-only authority
- avoid introducing runtime semantics
- preserve determinism and inspectability

ICE Strap accepts **structure first**, features last.

---

## License

This project is licensed under the terms specified in the LICENSE file.
