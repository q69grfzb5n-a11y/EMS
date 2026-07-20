import { apiClient } from "@/shared/api/client";
import type {
  AttendanceImportOut,
  AttendanceRecordOut,
  AttendanceZeroFlagOut,
  ImportPreviewOut,
  IncentivePeriodCreateRequest,
  IncentivePeriodOut,
  IncentivePeriodPoolsRequest,
} from "@/modules/attendance/types";

export async function listPeriods(): Promise<IncentivePeriodOut[]> {
  const { data } = await apiClient.get<IncentivePeriodOut[]>("/attendance/periods");
  return data;
}

export async function createPeriod(
  payload: IncentivePeriodCreateRequest,
): Promise<IncentivePeriodOut> {
  const { data } = await apiClient.post<IncentivePeriodOut>("/attendance/periods", payload);
  return data;
}

export async function getPeriod(periodId: number): Promise<IncentivePeriodOut> {
  const { data } = await apiClient.get<IncentivePeriodOut>(`/attendance/periods/${periodId}`);
  return data;
}

export async function lockPeriod(periodId: number): Promise<IncentivePeriodOut> {
  const { data } = await apiClient.post<IncentivePeriodOut>(
    `/attendance/periods/${periodId}/lock`,
  );
  return data;
}

export async function unlockPeriod(periodId: number): Promise<IncentivePeriodOut> {
  const { data } = await apiClient.post<IncentivePeriodOut>(
    `/attendance/periods/${periodId}/unlock`,
  );
  return data;
}

export async function updatePeriodPools(
  periodId: number,
  payload: IncentivePeriodPoolsRequest,
): Promise<IncentivePeriodOut> {
  const { data } = await apiClient.patch<IncentivePeriodOut>(
    `/attendance/periods/${periodId}/pools`,
    payload,
  );
  return data;
}

export async function uploadAttendanceFile(
  periodId: number,
  file: File,
  dryRun: boolean,
): Promise<ImportPreviewOut | AttendanceImportOut> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await apiClient.post<ImportPreviewOut | AttendanceImportOut>(
    `/attendance/periods/${periodId}/imports`,
    form,
    { params: { dry_run: dryRun }, headers: { "Content-Type": "multipart/form-data" } },
  );
  return data;
}

export async function listImports(periodId: number): Promise<AttendanceImportOut[]> {
  const { data } = await apiClient.get<AttendanceImportOut[]>(
    `/attendance/periods/${periodId}/imports`,
  );
  return data;
}

export async function listRecords(periodId: number): Promise<AttendanceRecordOut[]> {
  const { data } = await apiClient.get<AttendanceRecordOut[]>(
    `/attendance/periods/${periodId}/records`,
  );
  return data;
}

export async function listZeroFlags(employeeId?: number): Promise<AttendanceZeroFlagOut[]> {
  const { data } = await apiClient.get<AttendanceZeroFlagOut[]>("/attendance/zero-flags", {
    params: employeeId ? { employee_id: employeeId } : undefined,
  });
  return data;
}

export async function overrideZeroFlag(
  flagId: number,
  reason: string,
): Promise<AttendanceZeroFlagOut> {
  const { data } = await apiClient.post<AttendanceZeroFlagOut>(
    `/attendance/zero-flags/${flagId}/override`,
    { reason },
  );
  return data;
}
