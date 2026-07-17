export interface NavItem {
  key: string;
  labelKey: string;
  path: string;
}

export const NAV_ITEMS: NavItem[] = [
  { key: "dashboard", labelKey: "nav.dashboard", path: "/" },
];
