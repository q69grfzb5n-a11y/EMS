from enum import StrEnum


class EmploymentStatus(StrEnum):
    ACTIVE = "active"
    TERMINATED = "terminated"


class TemplateVersionStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class InputMode(StrEnum):
    MARKS = "marks"
    SCALE_1_5 = "scale_1_5"


class AutoSource(StrEnum):
    NONE = "none"
    OVERTIME_HOURS = "overtime_hours"
    ABSENCE_PENALTY = "absence_penalty"


class PeriodStatus(StrEnum):
    OPEN = "open"
    LOCKED = "locked"


class AttendanceImportStatus(StrEnum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"


class EvaluationKind(StrEnum):
    REGULAR = "regular"
    SELF_APPRAISAL = "self_appraisal"


class EvaluationStatus(StrEnum):
    """Union of every status reachable in either transition table (REGULAR or
    SELF) — one shared status column, two distinct tables in workflow.py."""

    DRAFT = "draft"
    SUBMITTED = "submitted"
    RETURNED = "returned"
    MANAGER_APPROVED = "manager_approved"
    PMO_REVIEWED = "pmo_reviewed"
    FM_APPROVED = "fm_approved"


class RoleCode(StrEnum):
    HR = "hr"
    ADMIN = "admin"
    PMO = "pmo"
    FACTORY_MANAGER = "factory_manager"
    DEPT_MANAGER = "dept_manager"
    REVIEWER = "reviewer"
    FINANCE = "finance"
    KEY_PERSON = "key_person"
    EMPLOYEE = "employee"
