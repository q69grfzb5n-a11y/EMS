import { describe, expect, it } from "vitest";

import { NAV_ITEMS } from "@/app/layout/navigation";

describe("NAV_ITEMS", () => {
  it("includes the dashboard entry", () => {
    expect(NAV_ITEMS.some((item) => item.key === "dashboard")).toBe(true);
  });
});
