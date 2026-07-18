import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it } from "vitest";

import { apiClient } from "@/shared/api/client";
import { useAuthStore } from "@/shared/auth/authStore";

let refreshCallCount = 0;

const server = setupServer(
  http.get("/api/v1/protected", ({ request }) => {
    const auth = request.headers.get("Authorization");
    if (auth === "Bearer new-access-token") {
      return HttpResponse.json({ ok: true });
    }
    return HttpResponse.json(
      { error: { code: "unauthorized", message: "Invalid or expired token" } },
      { status: 401 },
    );
  }),
  http.post("/api/v1/auth/refresh", () => {
    refreshCallCount += 1;
    return HttpResponse.json({
      access_token: "new-access-token",
      token_type: "bearer",
      must_change_password: false,
    });
  }),
);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

beforeEach(() => {
  refreshCallCount = 0;
  useAuthStore.getState().clear();
  useAuthStore.getState().setAccessToken("expired-token");
});

describe("apiClient refresh interceptor", () => {
  it("refreshes once and retries all concurrent 401s (single-flight)", async () => {
    const [first, second] = await Promise.all([
      apiClient.get("/protected"),
      apiClient.get("/protected"),
    ]);

    expect(first.data).toEqual({ ok: true });
    expect(second.data).toEqual({ ok: true });
    expect(refreshCallCount).toBe(1);
    expect(useAuthStore.getState().accessToken).toBe("new-access-token");
  });
});
