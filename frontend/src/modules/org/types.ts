export interface DepartmentOut {
  id: number;
  code: string;
  name_en: string;
  name_ar: string;
  is_active: boolean;
}

export interface DepartmentCreateRequest {
  code: string;
  name_en: string;
  name_ar: string;
}

export interface DepartmentPatchRequest {
  name_en?: string;
  name_ar?: string;
  is_active?: boolean;
}

export interface PositionRateOut {
  id: number;
  position_id: number;
  effective_from: string;
  effective_to: string | null;
  incentive_pct: string | null;
  flat_ref_amount: string | null;
}

export interface PositionRateCreateRequest {
  effective_from: string;
  effective_to?: string | null;
  incentive_pct?: string | null;
  flat_ref_amount?: string | null;
}

export interface PositionOut {
  id: number;
  code: string;
  title_en: string;
  title_ar: string;
  is_active: boolean;
  current_rate: PositionRateOut | null;
}

export interface PositionCreateRequest {
  code: string;
  title_en: string;
  title_ar: string;
}

export interface PositionPatchRequest {
  title_en?: string;
  title_ar?: string;
  is_active?: boolean;
}
