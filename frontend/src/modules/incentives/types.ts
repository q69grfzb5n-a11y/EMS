export type IncentiveRunStatus = "draft" | "pmo_audit" | "fm_approval" | "approved";
export type FormulaMode = "legacy_flat" | "pct_of_salary";

export interface DepartmentBrief {
  id: number;
  code: string;
  name_en: string;
  name_ar: string;
}

export interface EmployeeBrief {
  id: number;
  staff_no: string;
  full_name_en: string | null;
  full_name_ar: string;
  department: DepartmentBrief;
}

export interface ExceptionOut {
  employee_id: number;
  staff_no: string;
  reason: string | null;
}

export interface IncentiveLineItemOut {
  id: number;
  employee: EmployeeBrief;
  evaluation_id: number | null;
  evaluation_pct: string;
  formula_mode: FormulaMode;
  flat_ref_amount: string | null;
  base_salary: string | null;
  position_incentive_pct: string | null;
  attendance_factor: string;
  target_ratio: string;
  computed_amount: string;
  override_amount: string | null;
  override_reason: string | null;
  final_amount: string;
  is_excluded: boolean;
  exclude_reason: string | null;
  row_version: number;
}

export interface IncentiveRunOut {
  id: number;
  period_id: number;
  run_no: number;
  status: IncentiveRunStatus;
  params: {
    formula_mode: FormulaMode;
    rounding_step: string;
    rounding_mode: string;
    engine_version: string;
  };
  exceptions: ExceptionOut[];
  created_by_user_id: number;
  total_final_amount: string;
  lines: IncentiveLineItemOut[];
}

export interface RunCreateRequest {
  period_id: number;
  formula_mode?: FormulaMode;
  rounding_step?: number;
  rounding_mode?: string;
}

export interface LineUpdateRequest {
  row_version: number;
  attendance_factor?: string | null;
  override_amount?: string | null;
  override_reason?: string | null;
  clear_override?: boolean;
  is_excluded?: boolean | null;
  exclude_reason?: string | null;
}
