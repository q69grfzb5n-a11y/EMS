export type PeriodStatus = "open" | "locked";
export type AttendanceImportStatus = "active" | "superseded";
export type IssueSeverity = "error" | "warning";

export interface IncentivePeriodOut {
  id: number;
  year: number;
  month: number;
  target_pool: string | null;
  actual_pool: string | null;
  status: PeriodStatus;
}

export interface IncentivePeriodCreateRequest {
  year: number;
  month: number;
}

export interface RowIssueOut {
  row_number: number;
  staff_no: string | null;
  severity: IssueSeverity;
  message: string;
}

export interface ImportPreviewOut {
  period_id: number;
  total_rows: number;
  matched_count: number;
  unmatched_count: number;
  unmatched_staff_nos: string[];
  issues: RowIssueOut[];
  has_errors: boolean;
}

export interface AttendanceImportOut {
  id: number;
  period_id: number;
  original_filename: string;
  uploaded_by_user_id: number;
  row_count: number;
  error_report: Record<string, unknown>[] | null;
  status: AttendanceImportStatus;
  created_at: string;
}

export interface AttendanceRecordEmployeeBrief {
  id: number;
  staff_no: string;
  full_name_en: string | null;
  full_name_ar: string;
}

export interface AttendanceRecordOut {
  id: number;
  period_id: number;
  employee: AttendanceRecordEmployeeBrief;
  present: number;
  off_days: number;
  absent: number;
  leave: number;
  public_holiday: number;
  deduct_min: string;
  over_time: string;
  approved: number;
  pending_approval: number;
  submitted: number;
  approved_over_time: string;
}

export interface AttendanceZeroFlagOut {
  id: number;
  employee_id: number;
  period_from_id: number;
  period_to_id: number;
  total_leave_absence_days: number;
  allowance_days: number;
  is_overridden: boolean;
  override_reason: string | null;
}
