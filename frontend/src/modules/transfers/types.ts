import type { EmployeeBrief } from "@/shared/types/approvals";

export type { EmployeeBrief };

export type TransferStatus = "draft" | "submitted" | "returned" | "pmo_reviewed" | "fm_approved" | "applied";

export interface DepartmentBrief {
  id: number;
  code: string;
  name_en: string;
  name_ar: string;
}

export interface TransferRequestOut {
  id: number;
  employee: EmployeeBrief;
  from_department: DepartmentBrief;
  to_department: DepartmentBrief;
  effective_date: string;
  reason: string | null;
  status: TransferStatus;
  requested_by_user_id: number;
}

export interface TransferCreateRequest {
  employee_id: number;
  to_department_id: number;
  effective_date: string;
  reason?: string | null;
}
