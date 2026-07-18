export interface TokenResponse {
  access_token: string;
  token_type: string;
  must_change_password: boolean;
}

export interface MeResponse {
  id: number;
  staff_no: string;
  roles: string[];
  must_change_password: boolean;
}

export interface UserOut {
  id: number;
  staff_no: string;
  is_active: boolean;
  must_change_password: boolean;
  roles: string[];
}

export interface RoleOut {
  id: number;
  code: string;
  name_en: string;
  name_ar: string;
}
