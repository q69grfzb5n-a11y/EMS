import { Empty, Timeline, Typography } from "antd";
import { useTranslation } from "react-i18next";

import type { ApprovalActionOut } from "@/modules/evaluations/types";
import { Ltr } from "@/shared/ui/Ltr";

export function ApprovalTimeline({ history }: { history: ApprovalActionOut[] }) {
  const { t } = useTranslation(["common", "approvals"]);

  if (history.length === 0) {
    return <Empty description={t("approvals:timeline.empty")} />;
  }

  return (
    <Timeline
      items={history.map((action) => ({
        children: (
          <div key={action.id}>
            <Typography.Text strong>{t(`approvals:actions.${action.action}`)}</Typography.Text>{" "}
            <Typography.Text type="secondary">
              ({t(`approvals:roles.${action.actor_role}`)})
            </Typography.Text>
            <div>
              <Ltr>
                {action.from_status} → {action.to_status}
              </Ltr>
            </div>
            {action.comment && <div>“{action.comment}”</div>}
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              <Ltr>{new Date(action.created_at).toLocaleString()}</Ltr>
            </Typography.Text>
          </div>
        ),
      }))}
    />
  );
}
