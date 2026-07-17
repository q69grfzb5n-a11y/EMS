# User Roles

> Status: skeleton — full role×permission matrix is added in Phase 1 alongside `require_roles` wiring and finalized in the Phase 9 permissions penetration pass.

## Roles (9, seeded in Phase 1)

HR, Admin, PMO, Factory Manager (FM), Dept Manager, Reviewer, Finance, Key Person, Employee — exact seed list and permissions: `backend/app/db/seed_data/` (Phase 1).

## Key rule

Role grants are **HR-only**, service-enforced and audited — **admin cannot assign roles**.

## Role × permission matrix

_To add once `frontend/src/shared/auth/permissions.ts` and backend `require_roles` guards land (Phase 1), then verified endpoint-by-endpoint in the Phase 9 penetration pass._
