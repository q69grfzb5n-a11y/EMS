# Workflows

> Status: skeleton — state diagrams are added in Phase 5 when `common/workflow.py` (the generic `TransitionTable` engine) lands.

## Engine

Hybrid approach: a status column on each entity (indexable, DB-constrainable) + one shared `approval_actions` history table + transition rules as data (`(state, action) → {to, roles, guard}`). `apply_transition()` validates role + guard, mutates status, logs, notifies.

## Flows

| Flow | States | Added in |
|---|---|---|
| Regular evaluation | draft → submitted → manager_approved (+ return loop) | Phase 5 |
| Self-appraisal | draft → submitted → pmo_reviewed → fm_approved (+ return loops) | Phase 6 |
| Transfer request | draft → submitted → pmo_reviewed → fm_approved → applied | Phase 6 |
| Incentive run | draft → pmo_audit → fm_approval → approved | Phase 7 |

## State diagrams

_To add per flow as each phase's transition table lands._
