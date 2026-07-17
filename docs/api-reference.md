# API Reference

> Status: skeleton — endpoint docs are added per module as each phase lands. Conventions: [PLAN.md §6.5](../PLAN.md).

## Conventions

- Base path `/api/v1`.
- Error envelope: `{"error": {"code": ..., "message": ..., "details": ...}}` with stable codes.
- List endpoints: `?page&size&sort` whitelist.
- Scoped list endpoints: reviewer → assigned, dept_manager → own dept, employee → self.
- Salary fields are **absent** (not masked) in responses for unauthorized roles.
- JWT access token 30 min / refresh token 14 days with rotation.

## Endpoints

_Documented per module starting Phase 1 (`/auth/*`). See the interactive OpenAPI docs at `/docs` on a running backend for the current live contract._
