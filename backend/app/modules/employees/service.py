from datetime import date
from decimal import Decimal

from sqlalchemy import Select, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.common.audit import write_audit
from app.common.enums import RoleCode
from app.common.errors import bad_request, conflict, forbidden, not_found
from app.modules.auth.models import User
from app.modules.employees.models import Employee, EmployeeSalary, EvaluationAssignment
from app.modules.org.service import get_department, get_position

# Roles with unrestricted visibility across the whole roster. Includes FINANCE
# (needed for payroll) even though evaluations/transfers deliberately exclude
# it — see the comment on those modules' own FULL_ACCESS_ROLES.
FULL_ACCESS_ROLES = {
    RoleCode.HR.value,
    RoleCode.ADMIN.value,
    RoleCode.PMO.value,
    RoleCode.FACTORY_MANAGER.value,
    RoleCode.FINANCE.value,
}
# Salary is confidential even from most roles that can see the roster itself.
SALARY_READ_ROLES = {RoleCode.HR.value, RoleCode.FINANCE.value, RoleCode.PMO.value}


def _employee_query() -> Select[tuple[Employee]]:
    return select(Employee).options(
        selectinload(Employee.department), selectinload(Employee.position)
    )


def get_employee(db: Session, employee_id: int) -> Employee:
    stmt = _employee_query().where(Employee.id == employee_id)
    employee = db.scalars(stmt).first()
    if employee is None:
        raise not_found("Employee not found")
    return employee


def get_employee_by_staff_no(db: Session, staff_no: str) -> Employee | None:
    stmt = _employee_query().where(Employee.staff_no == staff_no)
    return db.scalars(stmt).first()


def _own_department_id(db: Session, user: User) -> int | None:
    if user.employee_id is None:
        return None
    employee = db.get(Employee, user.employee_id)
    return employee.department_id if employee is not None else None


def get_reviewer_assignment(db: Session, employee_id: int) -> EvaluationAssignment | None:
    stmt = select(EvaluationAssignment).where(EvaluationAssignment.employee_id == employee_id)
    return db.scalars(stmt).first()


def can_view_employee(db: Session, user: User, employee: Employee) -> bool:
    role_codes = set(user.role_codes)
    if FULL_ACCESS_ROLES.intersection(role_codes):
        return True
    if RoleCode.DEPT_MANAGER.value in role_codes:
        return employee.department_id == _own_department_id(db, user)
    if RoleCode.REVIEWER.value in role_codes:
        assignment = get_reviewer_assignment(db, employee.id)
        return assignment is not None and assignment.reviewer_user_id == user.id
    return user.employee_id == employee.id


def list_employees_scoped(db: Session, user: User) -> list[Employee]:
    role_codes = set(user.role_codes)
    stmt = _employee_query().order_by(Employee.staff_no)

    if FULL_ACCESS_ROLES.intersection(role_codes):
        return list(db.scalars(stmt))

    if RoleCode.DEPT_MANAGER.value in role_codes:
        dept_id = _own_department_id(db, user)
        if dept_id is None:
            return []
        return list(db.scalars(stmt.where(Employee.department_id == dept_id)))

    if RoleCode.REVIEWER.value in role_codes:
        stmt = stmt.join(
            EvaluationAssignment, EvaluationAssignment.employee_id == Employee.id
        ).where(EvaluationAssignment.reviewer_user_id == user.id)
        return list(db.scalars(stmt))

    # employee / key_person: self only
    if user.employee_id is not None:
        return list(db.scalars(stmt.where(Employee.id == user.employee_id)))
    return []


def get_employee_scoped(db: Session, user: User, employee_id: int) -> Employee:
    employee = get_employee(db, employee_id)
    if not can_view_employee(db, user, employee):
        raise forbidden()
    return employee


def create_employee(
    db: Session,
    actor: User,
    *,
    staff_no: str,
    full_name_ar: str,
    full_name_en: str | None,
    department_id: int,
    position_id: int,
    contract_position_title: str | None,
    contract_years: int | None,
    contract_start_date: date | None,
) -> Employee:
    if get_employee_by_staff_no(db, staff_no) is not None:
        raise conflict("An employee with this staff number already exists", code="staff_no_taken")
    get_department(db, department_id)
    get_position(db, position_id)

    employee = Employee(
        staff_no=staff_no,
        full_name_ar=full_name_ar,
        full_name_en=full_name_en,
        department_id=department_id,
        position_id=position_id,
        contract_position_title=contract_position_title,
        contract_years=contract_years,
        contract_start_date=contract_start_date,
    )
    db.add(employee)
    db.flush()
    write_audit(
        db,
        actor_user_id=actor.id,
        action="create_employee",
        entity_type="employee",
        entity_id=employee.id,
        after={"staff_no": staff_no, "department_id": department_id, "position_id": position_id},
    )
    db.commit()
    return get_employee(db, employee.id)


def patch_employee(db: Session, actor: User, employee_id: int, **fields: object) -> Employee:
    employee = get_employee(db, employee_id)
    before = {k: getattr(employee, k) for k in fields if fields[k] is not None}

    if fields.get("department_id") is not None:
        get_department(db, fields["department_id"])  # type: ignore[arg-type]
    if fields.get("position_id") is not None:
        get_position(db, fields["position_id"])  # type: ignore[arg-type]

    for key, value in fields.items():
        if value is not None:
            setattr(employee, key, value)

    write_audit(
        db,
        actor_user_id=actor.id,
        action="patch_employee",
        entity_type="employee",
        entity_id=employee.id,
        before={k: str(v) for k, v in before.items()},
        after={k: str(getattr(employee, k)) for k in before},
    )
    db.commit()
    return get_employee(db, employee.id)


def assign_reviewer(db: Session, actor: User, employee_id: int, reviewer_user_id: int) -> Employee:
    employee = get_employee(db, employee_id)
    existing = get_reviewer_assignment(db, employee_id)
    before = existing.reviewer_user_id if existing is not None else None
    if existing is not None:
        existing.reviewer_user_id = reviewer_user_id
        existing.assigned_by_user_id = actor.id
    else:
        db.add(
            EvaluationAssignment(
                employee_id=employee_id,
                reviewer_user_id=reviewer_user_id,
                assigned_by_user_id=actor.id,
            )
        )
    write_audit(
        db,
        actor_user_id=actor.id,
        action="assign_reviewer",
        entity_type="employee",
        entity_id=employee_id,
        before={"reviewer_user_id": before},
        after={"reviewer_user_id": reviewer_user_id},
    )
    db.commit()
    return get_employee(db, employee.id)


def can_read_salary(user: User) -> bool:
    return bool(SALARY_READ_ROLES.intersection(user.role_codes))


def salary_as_of(db: Session, employee_id: int, as_of: date) -> EmployeeSalary | None:
    """First-day-of-month rule: caller passes the first day of the relevant month."""
    stmt = select(EmployeeSalary).where(
        EmployeeSalary.employee_id == employee_id,
        EmployeeSalary.effective_from <= as_of,
        (EmployeeSalary.effective_to.is_(None)) | (EmployeeSalary.effective_to > as_of),
    )
    return db.scalars(stmt).first()


def list_salaries(db: Session, actor: User, employee_id: int) -> list[EmployeeSalary]:
    get_employee(db, employee_id)
    if not can_read_salary(actor):
        raise forbidden()
    write_audit(
        db,
        actor_user_id=actor.id,
        action="read_salaries",
        entity_type="employee",
        entity_id=employee_id,
    )
    db.commit()
    stmt = (
        select(EmployeeSalary)
        .where(EmployeeSalary.employee_id == employee_id)
        .order_by(EmployeeSalary.effective_from.desc())
    )
    return list(db.scalars(stmt))


def create_salary(
    db: Session,
    actor: User,
    employee_id: int,
    *,
    effective_from: date,
    effective_to: date | None,
    base_salary: Decimal,
) -> EmployeeSalary:
    get_employee(db, employee_id)
    if effective_to is not None and effective_to <= effective_from:
        raise bad_request("effective_to must be after effective_from", code="invalid_date_range")

    salary = EmployeeSalary(
        employee_id=employee_id,
        effective_from=effective_from,
        effective_to=effective_to,
        base_salary=base_salary,
    )
    db.add(salary)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise conflict(
            "This date range overlaps an existing salary window for the employee",
            code="salary_overlap",
        ) from exc

    write_audit(
        db,
        actor_user_id=actor.id,
        action="create_salary",
        entity_type="employee_salary",
        entity_id=salary.id,
        after={
            "employee_id": employee_id,
            "effective_from": str(effective_from),
            "effective_to": str(effective_to) if effective_to else None,
        },
    )
    db.commit()
    return salary
