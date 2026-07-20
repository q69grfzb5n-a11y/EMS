export type InputMode = "marks" | "scale_1_5";
export type AutoSource = "none" | "overtime_hours" | "absence_penalty";
export type TemplateVersionStatus = "draft" | "active" | "archived";

export interface KpiCriterionOut {
  id: number;
  name_en: string;
  name_ar: string;
  guidance_en: string | null;
  guidance_ar: string | null;
  max_marks: number;
  input_mode: InputMode;
  allow_negative: boolean;
  auto_source: AutoSource;
  auto_params: Record<string, unknown> | null;
  sort_order: number;
}

export interface KpiCriterionCreateRequest {
  name_en: string;
  name_ar: string;
  guidance_en?: string | null;
  guidance_ar?: string | null;
  max_marks: number;
  input_mode?: InputMode;
  allow_negative?: boolean;
  auto_source?: AutoSource;
  auto_params?: Record<string, unknown> | null;
  sort_order?: number;
}

export interface KpiCriterionPatchRequest {
  name_en?: string;
  name_ar?: string;
  max_marks?: number;
  allow_negative?: boolean;
}

export interface KpiTemplateVersionOut {
  id: number;
  template_id: number;
  version_no: number;
  status: TemplateVersionStatus;
  criteria: KpiCriterionOut[];
  total_marks: number;
}

export interface KpiTemplateVersionSummary {
  id: number;
  version_no: number;
  status: TemplateVersionStatus;
  total_marks: number;
}

export interface KpiTemplateOut {
  id: number;
  code: string;
  name_en: string;
  name_ar: string;
  active_version: KpiTemplateVersionSummary | null;
}

export interface KpiTemplateCreateRequest {
  code: string;
  name_en: string;
  name_ar: string;
}

export interface KpiTemplateAssignmentOut {
  id: number;
  position_id: number;
  template_id: number;
  effective_from: string;
  effective_to: string | null;
}

export interface KpiTemplateAssignmentCreateRequest {
  template_id: number;
  effective_from: string;
  effective_to?: string | null;
}
