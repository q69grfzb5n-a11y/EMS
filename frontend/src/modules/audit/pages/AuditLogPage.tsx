import { useState } from "react";
import { DatePicker, Form, Input, InputNumber, Modal, Table, Typography } from "antd";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import dayjs from "dayjs";

import { listAuditLog } from "@/modules/audit/api/auditApi";
import type { AuditLogOut } from "@/modules/audit/types";
import { Ltr } from "@/shared/ui/Ltr";

interface FilterValues {
  entity_type?: string;
  actor_user_id?: number;
  date_range?: [dayjs.Dayjs, dayjs.Dayjs];
}

export function AuditLogPage() {
  const { t } = useTranslation(["common", "audit"]);
  const [filters, setFilters] = useState<FilterValues>({});
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [selected, setSelected] = useState<AuditLogOut | null>(null);

  const query = useQuery({
    queryKey: ["audit-log", filters, page, pageSize],
    queryFn: () =>
      listAuditLog({
        entity_type: filters.entity_type || undefined,
        actor_user_id: filters.actor_user_id,
        date_from: filters.date_range?.[0]?.startOf("day").toISOString(),
        date_to: filters.date_range?.[1]?.endOf("day").toISOString(),
        limit: pageSize,
        offset: (page - 1) * pageSize,
      }),
  });

  return (
    <div>
      <Typography.Title level={3}>{t("audit:title")}</Typography.Title>

      <Form
        layout="inline"
        style={{ marginBottom: 16 }}
        onFinish={(values: FilterValues) => {
          setFilters(values);
          setPage(1);
        }}
      >
        <Form.Item name="entity_type">
          <Input placeholder={t("audit:entityType")} style={{ direction: "ltr" }} />
        </Form.Item>
        <Form.Item name="actor_user_id">
          <InputNumber placeholder={t("audit:actorUserId")} min={1} />
        </Form.Item>
        <Form.Item name="date_range">
          <DatePicker.RangePicker />
        </Form.Item>
        <Form.Item>
          <button type="submit" style={{ display: "none" }} />
        </Form.Item>
      </Form>

      <Table<AuditLogOut>
        rowKey="id"
        size="small"
        loading={query.isLoading}
        dataSource={query.data?.items ?? []}
        onRow={(record) => ({ onClick: () => setSelected(record), style: { cursor: "pointer" } })}
        pagination={{
          current: page,
          pageSize,
          total: query.data?.total ?? 0,
          onChange: (p, ps) => {
            setPage(p);
            setPageSize(ps);
          },
        }}
        columns={[
          {
            title: t("audit:createdAt"),
            key: "created_at",
            render: (_: unknown, r: AuditLogOut) => <Ltr>{new Date(r.created_at).toLocaleString()}</Ltr>,
          },
          {
            title: t("audit:actor"),
            key: "actor",
            render: (_: unknown, r: AuditLogOut) => <Ltr>{r.actor_staff_no ?? "—"}</Ltr>,
          },
          { title: t("audit:action"), dataIndex: "action" },
          { title: t("audit:entityType"), dataIndex: "entity_type" },
          {
            title: t("audit:entityId"),
            dataIndex: "entity_id",
            render: (v: string) => <Ltr>{v}</Ltr>,
          },
        ]}
      />

      <Modal
        title={t("audit:details")}
        open={selected !== null}
        onCancel={() => setSelected(null)}
        footer={null}
        width={700}
      >
        {selected && (
          <>
            <Typography.Title level={5}>{t("audit:before")}</Typography.Title>
            <pre style={{ direction: "ltr", overflowX: "auto" }}>
              {JSON.stringify(selected.before, null, 2) ?? "—"}
            </pre>
            <Typography.Title level={5}>{t("audit:after")}</Typography.Title>
            <pre style={{ direction: "ltr", overflowX: "auto" }}>
              {JSON.stringify(selected.after, null, 2) ?? "—"}
            </pre>
          </>
        )}
      </Modal>
    </div>
  );
}

export default AuditLogPage;
