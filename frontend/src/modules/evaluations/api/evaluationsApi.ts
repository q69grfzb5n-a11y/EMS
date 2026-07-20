import { apiClient } from "@/shared/api/client";
import type {
  ApprovalActionOut,
  BulkCreateRequest,
  BulkCreateResponse,
  EvaluationCreateRequest,
  EvaluationOut,
  EvaluationUpdateRequest,
} from "@/modules/evaluations/types";

export async function listEvaluations(periodId?: number): Promise<EvaluationOut[]> {
  const { data } = await apiClient.get<EvaluationOut[]>("/evaluations", {
    params: periodId ? { period_id: periodId } : undefined,
  });
  return data;
}

export async function createEvaluation(payload: EvaluationCreateRequest): Promise<EvaluationOut> {
  const { data } = await apiClient.post<EvaluationOut>("/evaluations", payload);
  return data;
}

export async function bulkCreateEvaluations(payload: BulkCreateRequest): Promise<BulkCreateResponse> {
  const { data } = await apiClient.post<BulkCreateResponse>("/evaluations/bulk", payload);
  return data;
}

export async function getEvaluation(id: number): Promise<EvaluationOut> {
  const { data } = await apiClient.get<EvaluationOut>(`/evaluations/${id}`);
  return data;
}

export async function updateEvaluation(
  id: number,
  payload: EvaluationUpdateRequest,
): Promise<EvaluationOut> {
  const { data } = await apiClient.patch<EvaluationOut>(`/evaluations/${id}`, payload);
  return data;
}

async function transition(id: number, action: string, comment?: string): Promise<EvaluationOut> {
  const { data } = await apiClient.post<EvaluationOut>(`/evaluations/${id}/${action}`, { comment });
  return data;
}

export const submitEvaluation = (id: number, comment?: string) => transition(id, "submit", comment);
export const approveEvaluation = (id: number, comment?: string) => transition(id, "approve", comment);
export const returnEvaluation = (id: number, comment?: string) => transition(id, "return", comment);
export const reviewEvaluation = (id: number, comment?: string) => transition(id, "review", comment);

export async function listPendingApprovals(): Promise<EvaluationOut[]> {
  const { data } = await apiClient.get<EvaluationOut[]>("/approvals/pending");
  return data;
}

export async function getEvaluationHistory(id: number): Promise<ApprovalActionOut[]> {
  const { data } = await apiClient.get<ApprovalActionOut[]>(`/approvals/evaluation/${id}/history`);
  return data;
}
