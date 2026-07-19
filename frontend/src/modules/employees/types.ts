export interface DepartmentBrief {
  id: number;
  code: string;
  name_en: string;
  name_ar: string;
}

export interface PositionBrief {
  id: number;
  code: string;
  title_en: string;
  title_ar: string;
}

export interface EmployeeOut {
  id: number;
  staff_no: string;
  full_name_en: string | null;
  full_name_ar: string;
  department: DepartmentBrief;
  position: PositionBrief;
  contract_position_title: string | null;
  contract_years: number | null;
  contract_start_date: string | null;
  employment_status: string;
  reviewer_user_id: number | null;
}

export interface EmployeeCreateRequest {
  staff_no: string;
  full_name_ar: string;
  full_name_en?: string | null;
  department_id: number;
  position_id: number;
  contract_position_title?: string | null;
  contract_years?: number | null;
  contract_start_date?: string | null;
}

export interface EmployeePatchRequest {
  full_name_ar?: string;
  full_name_en?: string | null;
  department_id?: number;
  position_id?: number;
  contract_position_title?: string | null;
  contract_years?: number | null;
  contract_start_date?: string | null;
  employment_status?: string;
}

export interface EmployeeSalaryOut {
  id: number;
  employee_id: number;
  effective_from: string;
  effective_to: string | null;
  base_salary: string;
}

export interface EmployeeSalaryCreateRequest {
  effective_from: string;
  effective_to?: string | null;
  base_salary: string;
}
