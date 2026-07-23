import type { ThemeConfig } from "antd";

/** SAJCO brand teal — see docs/deployment.md or PLAN.md for the org name. */
export const BRAND_COLOR = "#0F6B5C";
export const BRAND_COLOR_SOFT = "#E6F2EF";

export const appTheme: ThemeConfig = {
  token: {
    colorPrimary: BRAND_COLOR,
    borderRadius: 8,
    fontFamily:
      "'IBM Plex Sans Arabic', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
  },
  components: {
    Layout: {
      headerBg: BRAND_COLOR,
      headerColor: "#ffffff",
      siderBg: "#ffffff",
    },
    Menu: {
      itemSelectedBg: BRAND_COLOR_SOFT,
      itemSelectedColor: BRAND_COLOR,
      itemHoverBg: "#F2F8F7",
    },
  },
};
