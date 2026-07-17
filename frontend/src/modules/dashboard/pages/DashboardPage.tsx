import { Typography } from "antd";
import { useTranslation } from "react-i18next";

export function DashboardPage() {
  const { t } = useTranslation();

  return <Typography.Title level={3}>{t("nav.dashboard")}</Typography.Title>;
}

export default DashboardPage;
