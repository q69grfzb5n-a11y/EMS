# KPI Templates

> Status: skeleton — full doc is added in Phase 3 alongside the `kpi_templates` module.

## Model

Logical template → immutable versions (`draft` → `active` → `archived`, partial-unique one active per template) → criteria (`max_marks`, `input_mode` `marks`|`scale_1_5`, `allow_negative`, `auto_source`/`auto_params`). Criteria are editable only while a version is `draft`; used versions are immutable forever.

## Seed templates (Phase 3)

SKILLED, NON_SKILLED, KEY_FOREMAN (100-point, from Word drafts — see [PLAN.md §3.2](../PLAN.md) for the criteria table), LEGACY_TEAM (8 criteria, 1–5 scale, weights ×100 = max marks).

## Validator

New-style template criteria `max_marks` must sum to exactly 100 (enforced backend + frontend/zod).

_Full walkthrough with screenshots added once the template builder UI lands (Phase 3)._
