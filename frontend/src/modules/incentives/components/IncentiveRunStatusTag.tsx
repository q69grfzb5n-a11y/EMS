import { Tag } from "antd";
import { useTranslation } from "react-i18next";

function runStatusColor(status: string): string {
  switch (status) {
    case "draft":
      return "default";
    case "pmo_audit":
      return "gold";
    case "fm_approval":
      return "blue";
    case "approved":
      return "green";
    default:
      return "default";
  }
}

export function IncentiveRunStatusTag({ status }: { status: string }) {
  const { t } = useTranslation("incentives");
  return <Tag color={runStatusColor(status)}>{t(`status.${status}`)}</Tag>;
}
