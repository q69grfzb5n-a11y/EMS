from typing import Annotated

from fastapi import APIRouter, Depends

from app.common.enums import RoleCode
from app.core.deps import CurrentUser, DbSession, require_roles
from app.modules.auth.models import User
from app.modules.employees import service
from app.modules.employees.models import Employee, EmployeeSalary
from app.modules.employees.schemas import (
    DepartmentBrief,
    EmployeeCreateRequest,
    EmployeeOut,
    EmployeePatchRequest,
    EmployeeSalaryCreateRequest,
    EmployeeSalaryOut,
    PositionBrief,
    ReviewerAssignRequest,
)

HROnly = Annotated[User, Depends(require_roles(RoleCode.HR))]

router = APIRouter(prefix="/employees", tags=["employees"])


def _employee_to_out(db_reviewer_user_id: int | None, employee: Employee) -> EmployeeOut:
    return EmployeeOut(
        id=employee.id,
        staff_no=employee.staff_no,
        full_name_en=employee.full_name_en,
        full_name_ar=employee.full_name_ar,
        department=DepartmentBrief(
            id=employee.department.id,
            code=employee.department.code,
            name_en=employee.department.name_en,
            name_ar=employee.department.name_ar,
        ),
        position=PositionBrief(
            id=employee.position.id,
            code=employee.position.code,
            title_en=employee.position.title_en,
            title_ar=employee.position.title_ar,
        ),
        contract_position_title=employee.contract_position_title,
        contract_years=employee.contract_years,
        contract_start_date=employee.contract_start_date,
        employment_status=employee.employment_status,
        reviewer_user_id=db_reviewer_user_id,
    )


def _to_out(db: DbSession, employee: Employee) -> EmployeeOut:
    assignment = service.get_reviewer_assignment(db, employee.id)
    return _employee_to_out(assignment.reviewer_user_id if assignment else None, employee)


@router.get("", response_model=list[EmployeeOut])
def list_employees_endpoint(user: CurrentUser, db: DbSession) -> list[EmployeeOut]:
    return [_to_out(db, e) for e in service.list_employees_scoped(db, user)]


@router.get("/{employee_id}", response_model=EmployeeOut)
def get_employee_endpoint(employee_id: int, user: CurrentUser, db: DbSession) -> EmployeeOut:
    employee = service.get_employee_scoped(db, user, employee_id)
    return _to_out(db, employee)


@router.post("", response_model=EmployeeOut, status_code=201)
def create_employee_endpoint(
    payload: EmployeeCreateRequest, actor: HROnly, db: DbSession
) -> EmployeeOut:
    employee = service.create_employee(
        db,
        actor,
        staff_no=payload.staff_no,
        full_name_ar=payload.full_name_ar,
        full_name_en=payload.full_name_en,
        department_id=payload.department_id,
        position_id=payload.position_id,
        contract_position_title=payload.contract_position_title,
        contract_years=payload.contract_years,
        contract_start_date=payload.contract_start_date,
    )
    return _to_out(db, employee)


@router.patch("/{employee_id}", response_model=EmployeeOut)
def patch_employee_endpoint(
    employee_id: int, payload: EmployeePatchRequest, actor: HROnly, db: DbSession
) -> EmployeeOut:
    employee = service.patch_employee(db, actor, employee_id, **payload.model_dump())
    return _to_out(db, employee)


@router.put("/{employee_id}/reviewer", response_model=EmployeeOut)
def assign_reviewer_endpoint(
    employee_id: int, payload: ReviewerAssignRequest, actor: HROnly, db: DbSession
) -> EmployeeOut:
    employee = service.assign_reviewer(db, actor, employee_id, payload.reviewer_user_id)
    return _to_out(db, employee)


def _salary_to_out(salary: EmployeeSalary) -> EmployeeSalaryOut:
    return EmployeeSalaryOut(
        id=salary.id,
        employee_id=salary.employee_id,
        effective_from=salary.effective_from,
        effective_to=salary.effective_to,
        base_salary=salary.base_salary,
    )


@router.get("/{employee_id}/salaries", response_model=list[EmployeeSalaryOut])
def list_salaries_endpoint(
    employee_id: int, actor: CurrentUser, db: DbSession
) -> list[EmployeeSalaryOut]:
    return [_salary_to_out(s) for s in service.list_salaries(db, actor, employee_id)]


@router.post("/{employee_id}/salaries", response_model=EmployeeSalaryOut, status_code=201)
def create_salary_endpoint(
    employee_id: int, payload: EmployeeSalaryCreateRequest, actor: HROnly, db: DbSession
) -> EmployeeSalaryOut:
    salary = service.create_salary(
        db,
        actor,
        employee_id,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
        base_salary=payload.base_salary,
    )
    return _salary_to_out(salary)
