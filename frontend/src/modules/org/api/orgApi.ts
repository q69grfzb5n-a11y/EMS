import { apiClient } from "@/shared/api/client";
import type {
  DepartmentCreateRequest,
  DepartmentOut,
  DepartmentPatchRequest,
  PositionCreateRequest,
  PositionOut,
  PositionPatchRequest,
  PositionRateCreateRequest,
  PositionRateOut,
} from "@/modules/org/types";

export async function listDepartments(): Promise<DepartmentOut[]> {
  const { data } = await apiClient.get<DepartmentOut[]>("/departments");
  return data;
}

export async function createDepartment(payload: DepartmentCreateRequest): Promise<DepartmentOut> {
  const { data } = await apiClient.post<DepartmentOut>("/departments", payload);
  return data;
}

export async function patchDepartment(
  id: number,
  payload: DepartmentPatchRequest,
): Promise<DepartmentOut> {
  const { data } = await apiClient.patch<DepartmentOut>(`/departments/${id}`, payload);
  return data;
}

export async function listPositions(): Promise<PositionOut[]> {
  const { data } = await apiClient.get<PositionOut[]>("/positions");
  return data;
}

export async function createPosition(payload: PositionCreateRequest): Promise<PositionOut> {
  const { data } = await apiClient.post<PositionOut>("/positions", payload);
  return data;
}

export async function patchPosition(
  id: number,
  payload: PositionPatchRequest,
): Promise<PositionOut> {
  const { data } = await apiClient.patch<PositionOut>(`/positions/${id}`, payload);
  return data;
}

export async function listPositionRates(positionId: number): Promise<PositionRateOut[]> {
  const { data } = await apiClient.get<PositionRateOut[]>(`/positions/${positionId}/rates`);
  return data;
}

export async function createPositionRate(
  positionId: number,
  payload: PositionRateCreateRequest,
): Promise<PositionRateOut> {
  const { data } = await apiClient.post<PositionRateOut>(
    `/positions/${positionId}/rates`,
    payload,
  );
  return data;
}
