import { Alert, Button, Card, Empty } from "antd";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { listPeriods } from "@/modules/attendance/api/attendanceApi";
import { getPeriodSummary } from "@/modules/reports/api/reportsApi";
import { useLocalizedField } from "@/shared/hooks/useLocalizedField";

export function DeptTotalsChart() {
  const { t } = useTranslation(["common", "dashboard"]);
  const localized = useLocalizedField();
  const periodsQuery = useQuery({ queryKey: ["attendance", "periods"], queryFn: listPeriods });
  const latestPeriodId = periodsQuery.data?.[0]?.id ?? null;

  const summaryQuery = useQuery({
    queryKey: ["reports", "period-summary", latestPeriodId],
    queryFn: () => getPeriodSummary(latestPeriodId as number),
    enabled: latestPeriodId !== null,
  });

  const chartData = (summaryQuery.data?.departments ?? []).map((d) => ({
    name: localized(d.name_en, d.name_ar),
    total: Number(d.total_amount),
  }));

  const isError = periodsQuery.isError || summaryQuery.isError;

  return (
    <Card
      title={t("dashboard:deptTotals.title")}
      loading={periodsQuery.isLoading || summaryQuery.isLoading}
    >
      {isError ? (
        <Alert
          type="error"
          showIcon
          message={t("common:common.loadError")}
          action={
            <Button
              size="small"
              onClick={() => {
                void periodsQuery.refetch();
                void summaryQuery.refetch();
              }}
            >
              {t("common:common.retry")}
            </Button>
          }
        />
      ) : chartData.length > 0 ? (
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="total" fill="#1677ff" />
          </BarChart>
        </ResponsiveContainer>
      ) : (
        <Empty description={t("dashboard:deptTotals.empty")} />
      )}
    </Card>
  );
}

export default DeptTotalsChart;
