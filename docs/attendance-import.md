# Attendance Import

> Status: skeleton — full contract doc is added in Phase 4 alongside `backend/app/modules/attendance/importer.py`.

## Source

Monthly Oracle export, sheet name `Employees Time Card Summary Rep`, ~420 rows, 17 fixed columns (verbatim header match, fail-fast on drift). Join key: `Person No.` (staff number; int-or-text → normalized string). See [PLAN.md §3.3](../PLAN.md) for the full column list.

## Contract rules

- Row `Month` must equal the declared period.
- Bucket-sum sanity check: Present + Off + Absent + Leave + Holiday == days-in-month (warning, not a hard fail).
- Department/name are **never** read from this file into master data — Oracle org names are informational only.
- sha256-identical re-upload → `409`; changed file → transactional upsert + prior import marked `superseded`; locked period → `409`.

## Dry-run → commit flow

_To add once the importer and `POST /attendance/imports?dry_run=` endpoint land (Phase 4)._
