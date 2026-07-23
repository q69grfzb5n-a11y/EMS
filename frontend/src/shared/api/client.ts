import axios, { type AxiosRequestConfig } from "axios";

import { useAuthStore } from "@/shared/auth/authStore";
import type { TokenResponse } from "@/modules/auth/types";

interface RetryableConfig extends AxiosRequestConfig {
  _retry?: boolean;
}

export const apiClient = axios.create({ baseURL: "/api/v1", withCredentials: true });

apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.set("Authorization", `Bearer ${token}`);
  }
  return config;
});

let refreshPromise: Promise<string> | null = null;

async function refreshAccessToken(): Promise<string> {
  const { data } = await axios.post<TokenResponse>("/api/v1/auth/refresh", null, {
    withCredentials: true,
  });
  useAuthStore.getState().setAccessToken(data.access_token);
  useAuthStore.getState().updateUser({ must_change_password: data.must_change_password });
  return data.access_token;
}

const AUTH_ENDPOINTS_WITHOUT_RETRY = ["/auth/refresh", "/auth/login"];

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config as RetryableConfig | undefined;
    const url = originalRequest?.url ?? "";

    // The backend enforces must_change_password on every endpoint except
    // /auth/me and /auth/change-password (see backend/app/core/deps.py). A
    // stale tab (or an admin forcing a reset on an already-logged-in user)
    // can hit this on any request; syncing the flag here means RequireAuth's
    // existing redirect takes over on the next render instead of the caller
    // just seeing a raw 403.
    if (
      error.response?.status === 403 &&
      error.response.data?.error?.code === "password_change_required"
    ) {
      useAuthStore.getState().updateUser({ must_change_password: true });
    }

    const isRetryableAuthFailure =
      error.response?.status === 401 &&
      originalRequest &&
      !originalRequest._retry &&
      !AUTH_ENDPOINTS_WITHOUT_RETRY.some((path) => url.includes(path));

    if (!isRetryableAuthFailure) {
      return Promise.reject(error);
    }

    originalRequest._retry = true;

    try {
      refreshPromise ??= refreshAccessToken().finally(() => {
        refreshPromise = null;
      });
      const newToken = await refreshPromise;
      originalRequest.headers = originalRequest.headers ?? {};
      (originalRequest.headers as Record<string, string>).Authorization = `Bearer ${newToken}`;
      return apiClient(originalRequest);
    } catch (refreshError) {
      useAuthStore.getState().clear();
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
      return Promise.reject(refreshError);
    }
  },
);
