import { Descriptions, Typography } from "antd";
import { useTranslation } from "react-i18next";

import type { IncentiveLineItemOut } from "@/modules/incentives/types";
import { Ltr } from "@/shared/ui/Ltr";

/** evalPct x base x factor x ratio -> rounded, per PLAN's IncentiveLineBreakdown spec. */
export function IncentiveLineBreakdown({ line }: { line: IncentiveLineItemOut }) {
  const { t } = useTranslation("incentives");
  const base =
    line.formula_mode === "legacy_flat"
      ? line.flat_ref_amount
      : line.base_salary && line.position_incentive_pct
        ? (Number(line.base_salary) * Number(line.position_incentive_pct)).toFixed(2)
        : null;

  return (
    <div>
      <Descriptions size="small" column={1} bordered>
        <Descriptions.Item label={t("breakdown.evaluationPct")}>
          <Ltr>{(Number(line.evaluation_pct) * 100).toFixed(2)}%</Ltr>
        </Descriptions.Item>
        <Descriptions.Item
          label={
            line.formula_mode === "legacy_flat"
              ? t("breakdown.flatRefAmount")
              : t("breakdown.baseSalaryTimesPct")
          }
        >
          <Ltr>{base ?? "—"}</Ltr>
        </Descriptions.Item>
        <Descriptions.Item label={t("breakdown.attendanceFactor")}>
          <Ltr>{line.attendance_factor}</Ltr>
        </Descriptions.Item>
        <Descriptions.Item label={t("breakdown.targetRatio")}>
          <Ltr>{line.target_ratio}</Ltr>
        </Descriptions.Item>
        <Descriptions.Item label={t("breakdown.computedAmount")}>
          <Ltr>{line.computed_amount}</Ltr>
        </Descriptions.Item>
        {line.override_amount && (
          <Descriptions.Item label={t("breakdown.overrideAmount")}>
            <Ltr>{line.override_amount}</Ltr> — {line.override_reason}
          </Descriptions.Item>
        )}
      </Descriptions>
      <Typography.Paragraph type="secondary" style={{ marginTop: 8, fontSize: 12 }}>
        <Ltr>
          {(Number(line.evaluation_pct) * 100).toFixed(1)}% × {base ?? "—"} ×{" "}
          {line.attendance_factor} × {line.target_ratio} = {line.final_amount}
        </Ltr>
      </Typography.Paragraph>
    </div>
  );
}
