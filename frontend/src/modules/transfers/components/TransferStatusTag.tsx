import { Tag } from "antd";
import { useTranslation } from "react-i18next";

function transferStatusColor(status: string): string {
  switch (status) {
    case "draft":
      return "default";
    case "submitted":
      return "gold";
    case "returned":
      return "red";
    case "pmo_reviewed":
      return "blue";
    case "fm_approved":
      return "green";
    case "applied":
      return "purple";
    default:
      return "default";
  }
}

export function TransferStatusTag({ status }: { status: string }) {
  const { t } = useTranslation("transfers");
  return <Tag color={transferStatusColor(status)}>{t(`status.${status}`)}</Tag>;
}
