export interface AuditLogOut {
  id: number;
  actor_user_id: number | null;
  actor_staff_no: string | null;
  action: string;
  entity_type: string;
  entity_id: string;
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
  created_at: string;
}

export interface AuditLogListOut {
  items: AuditLogOut[];
  total: number;
}

export interface AuditLogFilters {
  entity_type?: string;
  actor_user_id?: number;
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
}
