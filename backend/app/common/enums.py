from enum import StrEnum


class EmploymentStatus(StrEnum):
    ACTIVE = "active"
    TERMINATED = "terminated"


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
