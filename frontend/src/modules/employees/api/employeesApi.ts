import { apiClient } from "@/shared/api/client";
import type {
  EmployeeCreateRequest,
  EmployeeOut,
  EmployeePatchRequest,
  EmployeeSalaryCreateRequest,
  EmployeeSalaryOut,
} from "@/modules/employees/types";

export async function listEmployees(): Promise<EmployeeOut[]> {
  const { data } = await apiClient.get<EmployeeOut[]>("/employees");
  return data;
}

export async function getEmployee(id: number): Promise<EmployeeOut> {
  const { data } = await apiClient.get<EmployeeOut>(`/employees/${id}`);
  return data;
}

export async function createEmployee(payload: EmployeeCreateRequest): Promise<EmployeeOut> {
  const { data } = await apiClient.post<EmployeeOut>("/employees", payload);
  return data;
}

export async function patchEmployee(id: number, payload: EmployeePatchRequest): Promise<EmployeeOut> {
  const { data } = await apiClient.patch<EmployeeOut>(`/employees/${id}`, payload);
  return data;
}

export async function assignReviewer(id: number, reviewerUserId: number): Promise<EmployeeOut> {
  const { data } = await apiClient.put<EmployeeOut>(`/employees/${id}/reviewer`, {
    reviewer_user_id: reviewerUserId,
  });
  return data;
}

export async function listSalaries(employeeId: number): Promise<EmployeeSalaryOut[]> {
  const { data } = await apiClient.get<EmployeeSalaryOut[]>(`/employees/${employeeId}/salaries`);
  return data;
}

export async function createSalary(
  employeeId: number,
  payload: EmployeeSalaryCreateRequest,
): Promise<EmployeeSalaryOut> {
  const { data } = await apiClient.post<EmployeeSalaryOut>(
    `/employees/${employeeId}/salaries`,
    payload,
  );
  return data;
}
