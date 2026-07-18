import { apiClient } from "@/shared/api/client";
import type { MeResponse, RoleOut, TokenResponse, UserOut } from "@/modules/auth/types";

export async function login(staff_no: string, password: string): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>("/auth/login", { staff_no, password });
  return data;
}

export async function logout(): Promise<void> {
  await apiClient.post("/auth/logout");
}

export async function fetchMe(): Promise<MeResponse> {
  const { data } = await apiClient.get<MeResponse>("/auth/me");
  return data;
}

export async function changePassword(
  current_password: string,
  new_password: string,
): Promise<void> {
  await apiClient.post("/auth/change-password", { current_password, new_password });
}

export async function listUsers(): Promise<UserOut[]> {
  const { data } = await apiClient.get<UserOut[]>("/users");
  return data;
}

export async function createUser(staff_no: string, password: string): Promise<UserOut> {
  const { data } = await apiClient.post<UserOut>("/users", { staff_no, password });
  return data;
}

export async function patchUser(userId: number, is_active: boolean): Promise<UserOut> {
  const { data } = await apiClient.patch<UserOut>(`/users/${userId}`, { is_active });
  return data;
}

export async function assignRoles(userId: number, role_codes: string[]): Promise<UserOut> {
  const { data } = await apiClient.put<UserOut>(`/users/${userId}/roles`, { role_codes });
  return data;
}

export async function resetPassword(userId: number, new_password: string): Promise<UserOut> {
  const { data } = await apiClient.post<UserOut>(`/users/${userId}/reset-password`, {
    new_password,
  });
  return data;
}

export async function listRoles(): Promise<RoleOut[]> {
  const { data } = await apiClient.get<RoleOut[]>("/roles");
  return data;
}
