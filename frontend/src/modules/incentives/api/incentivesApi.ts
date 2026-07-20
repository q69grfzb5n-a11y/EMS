import { apiClient } from "@/shared/api/client";
import type {
  IncentiveLineItemOut,
  IncentiveRunOut,
  LineUpdateRequest,
  RunCreateRequest,
} from "@/modules/incentives/types";
import type { ApprovalActionOut } from "@/shared/types/approvals";

export async function listRuns(periodId?: number): Promise<IncentiveRunOut[]> {
  const { data } = await apiClient.get<IncentiveRunOut[]>("/incentive-runs", {
    params: periodId ? { period_id: periodId } : undefined,
  });
  return data;
}

export async function createRun(payload: RunCreateRequest): Promise<IncentiveRunOut> {
  const { data } = await apiClient.post<IncentiveRunOut>("/incentive-runs", payload);
  return data;
}

export async function getRun(id: number): Promise<IncentiveRunOut> {
  const { data } = await apiClient.get<IncentiveRunOut>(`/incentive-runs/${id}`);
  return data;
}

export async function recalculateRun(id: number): Promise<IncentiveRunOut> {
  const { data } = await apiClient.post<IncentiveRunOut>(`/incentive-runs/${id}/recalculate`);
  return data;
}

export async function updateLine(
  runId: number,
  lineId: number,
  payload: LineUpdateRequest,
): Promise<IncentiveRunOut> {
  const { data } = await apiClient.patch<IncentiveRunOut>(
    `/incentive-runs/${runId}/lines/${lineId}`,
    payload,
  );
  return data;
}

async function transition(id: number, action: string, comment?: string): Promise<IncentiveRunOut> {
  const { data } = await apiClient.post<IncentiveRunOut>(`/incentive-runs/${id}/${action}`, {
    comment,
  });
  return data;
}

export const submitAudit = (id: number, comment?: string) => transition(id, "submit-audit", comment);
export const completeAudit = (id: number, comment?: string) =>
  transition(id, "complete-audit", comment);
export const approveRun = (id: number, comment?: string) => transition(id, "approve", comment);
export const rejectRun = (id: number, comment?: string) => transition(id, "reject", comment);

export async function getRunHistory(id: number): Promise<ApprovalActionOut[]> {
  const { data } = await apiClient.get<ApprovalActionOut[]>(`/incentive-runs/${id}/history`);
  return data;
}

export async function listMyIncentives(): Promise<IncentiveLineItemOut[]> {
  const { data } = await apiClient.get<IncentiveLineItemOut[]>("/incentive-runs/my/incentives");
  return data;
}
