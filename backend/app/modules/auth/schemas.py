from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    staff_no: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    must_change_password: bool


class MeResponse(BaseModel):
    id: int
    staff_no: str
    roles: list[str]
    must_change_password: bool


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class UserCreateRequest(BaseModel):
    staff_no: str
    password: str = Field(min_length=8)


class UserPatchRequest(BaseModel):
    is_active: bool | None = None


class UserOut(BaseModel):
    id: int
    staff_no: str
    is_active: bool
    must_change_password: bool
    roles: list[str]
    employee_id: int | None = None
    employee_staff_no: str | None = None
    employee_name_en: str | None = None
    employee_name_ar: str | None = None


class RoleOut(BaseModel):
    id: int
    code: str
    name_en: str
    name_ar: str


class AssignRolesRequest(BaseModel):
    role_codes: list[str]


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=8)


class LinkEmployeeRequest(BaseModel):
    employee_id: int | None
