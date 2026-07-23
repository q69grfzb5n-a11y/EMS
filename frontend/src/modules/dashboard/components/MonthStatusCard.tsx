import { Alert, Button, Card, Empty, Tag } from "antd";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { listPeriods } from "@/modules/attendance/api/attendanceApi";
import { Ltr } from "@/shared/ui/Ltr";

export function MonthStatusCard() {
  const { t } = useTranslation(["common", "dashboard", "attendance"]);
  const query = useQuery({ queryKey: ["attendance", "periods"], queryFn: listPeriods });

  const latest = query.data?.[0];

  return (
    <Card title={t("dashboard:monthStatus.title")} loading={query.isLoading}>
      {query.isError ? (
        <Alert
          type="error"
          showIcon
          message={t("common:common.loadError")}
          action={
            <Button size="small" onClick={() => void query.refetch()}>
              {t("common:common.retry")}
            </Button>
          }
        />
      ) : latest ? (
        <>
          <Ltr>
            {String(latest.month).padStart(2, "0")}-{latest.year}
          </Ltr>{" "}
          <Tag color={latest.status === "locked" ? "default" : "green"}>
            {t(`attendance:periodStatus.${latest.status}`)}
          </Tag>
        </>
      ) : (
        <Empty description={t("dashboard:monthStatus.empty")} />
      )}
    </Card>
  );
}

export default MonthStatusCard;
