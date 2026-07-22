export interface DeptSummaryOut {
  department_id: number;
  code: string;
  name_en: string;
  name_ar: string;
  employee_count: number;
  total_amount: string;
}

export interface PeriodSummaryOut {
  period_id: number;
  year: number;
  month: number;
  run_id: number | null;
  run_status: string | null;
  departments: DeptSummaryOut[];
  grand_total: string;
}
