export interface EmployeeBrief {
  id: number;
  staff_no: string;
  full_name_en: string | null;
  full_name_ar: string;
}

export interface ApprovalActionOut {
  id: number;
  entity_type: string;
  entity_id: number;
  action: string;
  from_status: string;
  to_status: string;
  actor_user_id: number;
  actor_role: string;
  comment: string | null;
  created_at: string;
}

export interface PendingItemOut {
  id: number;
  entity_type: "evaluation" | "transfer";
  kind: string;
  status: string;
  employee: EmployeeBrief;
  created_at: string;
}
