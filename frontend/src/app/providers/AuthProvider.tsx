import { useEffect, type PropsWithChildren } from "react";
import { Spin } from "antd";
import axios from "axios";

import { fetchMe } from "@/modules/auth/api/authApi";
import { useAuthStore } from "@/shared/auth/authStore";
import type { TokenResponse } from "@/modules/auth/types";

export function AuthProvider({ children }: PropsWithChildren) {
  const status = useAuthStore((state) => state.status);
  const setSession = useAuthStore((state) => state.setSession);
  const setStatus = useAuthStore((state) => state.setStatus);

  useEffect(() => {
    let cancelled = false;

    async function silentRefresh() {
      setStatus("loading");
      try {
        const { data } = await axios.post<TokenResponse>("/api/v1/auth/refresh", null, {
          withCredentials: true,
        });
        useAuthStore.getState().setAccessToken(data.access_token);
        const me = await fetchMe();
        if (!cancelled) {
          setSession(data.access_token, me);
        }
      } catch {
        if (!cancelled) {
          setStatus("unauthenticated");
        }
      }
    }

    void silentRefresh();
    return () => {
      cancelled = true;
    };
  }, [setStatus, setSession]);

  if (status === "idle" || status === "loading") {
    return (
      <div style={{ display: "flex", justifyContent: "center", paddingTop: 80 }}>
        <Spin size="large" />
      </div>
    );
  }

  return children;
}
