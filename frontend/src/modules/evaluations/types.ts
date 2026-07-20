export type EvaluationKind = "regular" | "self_appraisal";
export type EvaluationStatus =
  | "draft"
  | "submitted"
  | "returned"
  | "manager_approved"
  | "pmo_reviewed"
  | "fm_approved";
export type InputMode = "marks" | "scale_1_5";

export interface EmployeeBrief {
  id: number;
  staff_no: string;
  full_name_en: string | null;
  full_name_ar: string;
}

export interface EvaluationScoreOut {
  criterion_id: number;
  name_en: string;
  name_ar: string;
  guidance_en: string | null;
  guidance_ar: string | null;
  max_marks: number;
  input_mode: InputMode;
  allow_negative: boolean;
  raw_input: string | null;
  awarded_marks: string | null;
  auto_suggested_marks: string | null;
  remarks: string | null;
}

export interface EvaluationOut {
  id: number;
  employee: EmployeeBrief;
  period_id: number;
  kind: EvaluationKind;
  status: EvaluationStatus;
  template_version_id: number;
  owner_user_id: number;
  activities: string[] | null;
  score_pct: string | null;
  grade: string | null;
  row_version: number;
  scores: EvaluationScoreOut[];
}

export interface EvaluationCreateRequest {
  employee_id: number;
  period_id: number;
  kind?: EvaluationKind;
}

export interface BulkCreateRequest {
  department_id: number;
  period_id: number;
  kind?: EvaluationKind;
}

export interface BulkCreateSkipped {
  employee_id: number;
  staff_no: string;
  reason: string | null;
}

export interface BulkCreateResponse {
  created: EvaluationOut[];
  skipped: BulkCreateSkipped[];
}

export interface ScoreUpdateRequest {
  criterion_id: number;
  raw_input?: number | null;
  remarks?: string | null;
}

export interface EvaluationUpdateRequest {
  row_version: number;
  scores: ScoreUpdateRequest[];
  activities?: string[] | null;
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
