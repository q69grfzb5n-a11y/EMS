# Database Schema

> Status: skeleton — ERD and table docs are added table-by-table as each phase's migrations land. Full table list and design notes: [PLAN.md §5](../PLAN.md).

## Conventions

BIGINT identity PKs · timestamptz UTC · statuses as varchar+CHECK (Python StrEnum) · percentages `numeric(6,4)` as 0–1 fractions · money `numeric(12,2)`, never floats · created/updated audit columns · SQLAlchemy `MetaData` naming conventions for deterministic Alembic (`pk_%`, `fk_%_%`, `uq_%`, `ix_%`, `ck_%`, see `backend/app/db/base.py`).

## ERD

```mermaid
erDiagram
    %% Populated incrementally — Phase 1 adds users/roles, Phase 2 adds org/employees, etc.
```

## Tables

_Added as each phase creates its migration. No hard deletes on domain data — statuses carry semantics (terminated/cancelled/superseded/is_active)._
