import { useState } from "react";
import { Button, Form, Input, InputNumber, Modal, Select, Space, Switch, Table, Tabs, Tag, Typography } from "antd";
import { DatePicker } from "antd";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import dayjs from "dayjs";

import {
  createPositionAssignment,
  listPositionAssignments,
  listTemplates,
} from "@/modules/kpi-templates/api/kpiTemplatesApi";
import {
  createDepartment,
  createPosition,
  createPositionRate,
  listDepartments,
  listPositionRates,
  listPositions,
  patchDepartment,
  patchPosition,
} from "@/modules/org/api/orgApi";
import type { DepartmentOut, PositionOut } from "@/modules/org/types";
import { Can } from "@/shared/auth/Can";
import { useLocalizedField } from "@/shared/hooks/useLocalizedField";
import { Ltr } from "@/shared/ui/Ltr";
import { LTR_INPUT_STYLES } from "@/shared/ui/ltrInput";

export function OrgPage() {
  const { t } = useTranslation(["common", "org"]);

  return (
    <div>
      <Typography.Title level={3}>{t("org:title")}</Typography.Title>
      <Tabs
        items={[
          { key: "departments", label: t("org:departments.title"), children: <DepartmentsTab /> },
          { key: "positions", label: t("org:positions.title"), children: <PositionsTab /> },
        ]}
      />
    </div>
  );
}

function DepartmentsTab() {
  const { t } = useTranslation(["common", "org"]);
  const queryClient = useQueryClient();
  const localized = useLocalizedField();
  const query = useQuery({ queryKey: ["org", "departments"], queryFn: listDepartments });
  const [editing, setEditing] = useState<DepartmentOut | null>(null);
  const [createOpen, setCreateOpen] = useState(false);

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["org", "departments"] });

  const createMutation = useMutation({
    mutationFn: createDepartment,
    onSuccess: () => {
      setCreateOpen(false);
      void invalidate();
    },
  });

  const patchMutation = useMutation({
    mutationFn: ({ id, ...payload }: { id: number; name_en: string; name_ar: string; is_active: boolean }) =>
      patchDepartment(id, payload),
    onSuccess: () => {
      setEditing(null);
      void invalidate();
    },
  });

  return (
    <div>
      <Space style={{ display: "flex", justifyContent: "flex-end", marginBottom: 12 }}>
        <Button type="primary" onClick={() => setCreateOpen(true)}>
          {t("org:departments.create")}
        </Button>
      </Space>
      <Table<DepartmentOut>
        rowKey="id"
        loading={query.isLoading}
        dataSource={query.data ?? []}
        pagination={false}
        columns={[
          { title: t("org:code"), dataIndex: "code", render: (v: string) => <Ltr>{v}</Ltr> },
          {
            title: t("org:name"),
            key: "name",
            render: (_: unknown, dept: DepartmentOut) => (
              <bdi>{localized(dept.name_en, dept.name_ar)}</bdi>
            ),
          },
          {
            title: t("common:common.active"),
            dataIndex: "is_active",
            render: (v: boolean) => <Tag color={v ? "green" : "default"}>{v ? t("common:common.active") : t("common:common.inactive")}</Tag>,
          },
          {
            title: t("common:common.edit"),
            key: "actions",
            render: (_: unknown, dept: DepartmentOut) => (
              <Button size="small" onClick={() => setEditing(dept)}>
                {t("common:common.edit")}
              </Button>
            ),
          },
        ]}
      />

      <Modal
        title={t("org:departments.create")}
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        footer={null}
        destroyOnHidden
      >
        <Form layout="vertical" onFinish={(values) => createMutation.mutate(values)}>
          <Form.Item name="code" label={t("org:code")} rules={[{ required: true }]}>
            <Input dir="ltr" styles={LTR_INPUT_STYLES} />
          </Form.Item>
          <Form.Item name="name_en" label={t("org:nameEn")} rules={[{ required: true }]}>
            <Input dir="ltr" styles={LTR_INPUT_STYLES} />
          </Form.Item>
          <Form.Item name="name_ar" label={t("org:nameAr")} rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={createMutation.isPending} block>
              {t("common:common.create")}
            </Button>
          </Form.Item>
        </Form>
      </Modal>

      {editing && (
        <Modal title={editing.code} open onCancel={() => setEditing(null)} footer={null} destroyOnHidden>
          <Form
            layout="vertical"
            initialValues={{ name_en: editing.name_en, name_ar: editing.name_ar, is_active: editing.is_active }}
            onFinish={(values) => patchMutation.mutate({ id: editing.id, ...values })}
          >
            <Form.Item name="name_en" label={t("org:nameEn")} rules={[{ required: true }]}>
              <Input dir="ltr" styles={LTR_INPUT_STYLES} />
            </Form.Item>
            <Form.Item name="name_ar" label={t("org:nameAr")} rules={[{ required: true }]}>
              <Input />
            </Form.Item>
            <Form.Item name="is_active" label={t("common:common.active")} valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item>
              <Button type="primary" htmlType="submit" loading={patchMutation.isPending} block>
                {t("common:common.save")}
              </Button>
            </Form.Item>
          </Form>
        </Modal>
      )}
    </div>
  );
}

function PositionsTab() {
  const { t } = useTranslation(["common", "org"]);
  const queryClient = useQueryClient();
  const localized = useLocalizedField();
  const query = useQuery({ queryKey: ["org", "positions"], queryFn: listPositions });
  const [editing, setEditing] = useState<PositionOut | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [ratesFor, setRatesFor] = useState<PositionOut | null>(null);
  const [kpiTemplateFor, setKpiTemplateFor] = useState<PositionOut | null>(null);

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["org", "positions"] });

  const createMutation = useMutation({
    mutationFn: createPosition,
    onSuccess: () => {
      setCreateOpen(false);
      void invalidate();
    },
  });

  const patchMutation = useMutation({
    mutationFn: ({ id, ...payload }: { id: number; title_en: string; title_ar: string; is_active: boolean }) =>
      patchPosition(id, payload),
    onSuccess: () => {
      setEditing(null);
      void invalidate();
    },
  });

  return (
    <div>
      <Space style={{ display: "flex", justifyContent: "flex-end", marginBottom: 12 }}>
        <Button type="primary" onClick={() => setCreateOpen(true)}>
          {t("org:positions.create")}
        </Button>
      </Space>
      <Table<PositionOut>
        rowKey="id"
        loading={query.isLoading}
        dataSource={query.data ?? []}
        pagination={false}
        columns={[
          { title: t("org:code"), dataIndex: "code", render: (v: string) => <Ltr>{v}</Ltr> },
          {
            title: t("org:title_"),
            key: "title",
            render: (_: unknown, position: PositionOut) => (
              <bdi>{localized(position.title_en, position.title_ar)}</bdi>
            ),
          },
          {
            title: t("org:positions.currentRate"),
            key: "rate",
            render: (_: unknown, position: PositionOut) => {
              const rate = position.current_rate;
              if (!rate) return <Tag>{t("org:positions.noRate")}</Tag>;
              return (
                <Ltr>
                  {rate.flat_ref_amount
                    ? t("common:common.currency", { amount: rate.flat_ref_amount })
                    : `${(Number(rate.incentive_pct) * 100).toFixed(2)}%`}
                </Ltr>
              );
            },
          },
          {
            title: t("common:common.active"),
            dataIndex: "is_active",
            render: (v: boolean) => <Tag color={v ? "green" : "default"}>{v ? t("common:common.active") : t("common:common.inactive")}</Tag>,
          },
          {
            title: t("common:common.edit"),
            key: "actions",
            render: (_: unknown, position: PositionOut) => (
              <Space>
                <Button size="small" onClick={() => setEditing(position)}>
                  {t("common:common.edit")}
                </Button>
                <Button size="small" onClick={() => setRatesFor(position)}>
                  {t("org:positions.rates")}
                </Button>
                <Button size="small" onClick={() => setKpiTemplateFor(position)}>
                  {t("org:positions.kpiTemplate")}
                </Button>
              </Space>
            ),
          },
        ]}
      />

      <Modal
        title={t("org:positions.create")}
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        footer={null}
        destroyOnHidden
      >
        <Form layout="vertical" onFinish={(values) => createMutation.mutate(values)}>
          <Form.Item name="code" label={t("org:code")} rules={[{ required: true }]}>
            <Input dir="ltr" styles={LTR_INPUT_STYLES} />
          </Form.Item>
          <Form.Item name="title_en" label={t("org:titleEn")} rules={[{ required: true }]}>
            <Input dir="ltr" styles={LTR_INPUT_STYLES} />
          </Form.Item>
          <Form.Item name="title_ar" label={t("org:titleAr")} rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={createMutation.isPending} block>
              {t("common:common.create")}
            </Button>
          </Form.Item>
        </Form>
      </Modal>

      {editing && (
        <Modal title={editing.code} open onCancel={() => setEditing(null)} footer={null} destroyOnHidden>
          <Form
            layout="vertical"
            initialValues={{ title_en: editing.title_en, title_ar: editing.title_ar, is_active: editing.is_active }}
            onFinish={(values) => patchMutation.mutate({ id: editing.id, ...values })}
          >
            <Form.Item name="title_en" label={t("org:titleEn")} rules={[{ required: true }]}>
              <Input dir="ltr" styles={LTR_INPUT_STYLES} />
            </Form.Item>
            <Form.Item name="title_ar" label={t("org:titleAr")} rules={[{ required: true }]}>
              <Input />
            </Form.Item>
            <Form.Item name="is_active" label={t("common:common.active")} valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item>
              <Button type="primary" htmlType="submit" loading={patchMutation.isPending} block>
                {t("common:common.save")}
              </Button>
            </Form.Item>
          </Form>
        </Modal>
      )}

      {ratesFor && <PositionRatesModal position={ratesFor} onClose={() => setRatesFor(null)} />}
      {kpiTemplateFor && (
        <PositionKpiTemplateModal position={kpiTemplateFor} onClose={() => setKpiTemplateFor(null)} />
      )}
    </div>
  );
}

function PositionRatesModal({ position, onClose }: { position: PositionOut; onClose: () => void }) {
  const { t } = useTranslation(["common", "org"]);
  const queryClient = useQueryClient();
  const ratesQuery = useQuery({
    queryKey: ["org", "positions", position.id, "rates"],
    queryFn: () => listPositionRates(position.id),
  });

  const createRateMutation = useMutation({
    mutationFn: (payload: { effective_from: string; effective_to?: string; flat_ref_amount?: number; incentive_pct?: number }) =>
      createPositionRate(position.id, {
        effective_from: payload.effective_from,
        effective_to: payload.effective_to ?? null,
        flat_ref_amount: payload.flat_ref_amount != null ? String(payload.flat_ref_amount) : null,
        incentive_pct: payload.incentive_pct != null ? String(payload.incentive_pct / 100) : null,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["org", "positions", position.id, "rates"] });
      void queryClient.invalidateQueries({ queryKey: ["org", "positions"] });
    },
  });

  return (
    <Modal title={`${position.code} — ${t("org:positions.rates")}`} open onCancel={onClose} footer={null} width={640}>
      <Table
        size="small"
        rowKey="id"
        loading={ratesQuery.isLoading}
        dataSource={ratesQuery.data ?? []}
        pagination={false}
        columns={[
          { title: t("org:rates.from"), dataIndex: "effective_from", render: (v: string) => <Ltr>{v}</Ltr> },
          {
            title: t("org:rates.to"),
            dataIndex: "effective_to",
            render: (v: string | null) => <Ltr>{v ?? t("org:rates.openEnded")}</Ltr>,
          },
          {
            title: t("org:positions.currentRate"),
            key: "amount",
            render: (_: unknown, rate: { flat_ref_amount: string | null; incentive_pct: string | null }) => (
              <Ltr>
                {rate.flat_ref_amount
                  ? `${rate.flat_ref_amount} SAR`
                  : rate.incentive_pct
                    ? `${(Number(rate.incentive_pct) * 100).toFixed(2)}%`
                    : "—"}
              </Ltr>
            ),
          },
        ]}
        style={{ marginBottom: 24 }}
      />

      <Typography.Title level={5}>{t("org:rates.addNew")}</Typography.Title>
      <Form
        layout="vertical"
        onFinish={(values: { effective_from: dayjs.Dayjs; effective_to?: dayjs.Dayjs; flat_ref_amount?: number; incentive_pct?: number }) =>
          createRateMutation.mutate({
            effective_from: values.effective_from.format("YYYY-MM-DD"),
            effective_to: values.effective_to ? values.effective_to.format("YYYY-MM-DD") : undefined,
            flat_ref_amount: values.flat_ref_amount,
            incentive_pct: values.incentive_pct,
          })
        }
      >
        <Space wrap>
          <Form.Item name="effective_from" label={t("org:rates.from")} rules={[{ required: true }]}>
            <DatePicker />
          </Form.Item>
          <Form.Item name="effective_to" label={t("org:rates.to")}>
            <DatePicker />
          </Form.Item>
          <Form.Item name="flat_ref_amount" label={t("org:rates.flatAmount")}>
            <InputNumber min={0} addonAfter={t("common:common.currencyUnit")} />
          </Form.Item>
          <Form.Item name="incentive_pct" label={t("org:rates.incentivePct")}>
            <InputNumber min={0} max={100} addonAfter="%" />
          </Form.Item>
        </Space>
        <Form.Item>
          <Button type="primary" htmlType="submit" loading={createRateMutation.isPending}>
            {t("common:common.create")}
          </Button>
        </Form.Item>
        {createRateMutation.isError && (
          <Typography.Text type="danger">{t("org:rates.overlapError")}</Typography.Text>
        )}
      </Form>
    </Modal>
  );
}

function PositionKpiTemplateModal({
  position,
  onClose,
}: {
  position: PositionOut;
  onClose: () => void;
}) {
  const { t } = useTranslation(["common", "org", "kpiTemplates"]);
  const localized = useLocalizedField();
  const queryClient = useQueryClient();
  const assignmentsQuery = useQuery({
    queryKey: ["org", "positions", position.id, "kpi-template-assignments"],
    queryFn: () => listPositionAssignments(position.id),
  });
  const templatesQuery = useQuery({ queryKey: ["kpi-templates"], queryFn: listTemplates });
  const templateName = (templateId: number) => {
    const tpl = templatesQuery.data?.find((t2) => t2.id === templateId);
    return tpl ? `${tpl.code} — ${localized(tpl.name_en, tpl.name_ar)}` : templateId;
  };

  const createMutation = useMutation({
    mutationFn: (payload: { template_id: number; effective_from: string; effective_to?: string }) =>
      createPositionAssignment(position.id, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["org", "positions", position.id, "kpi-template-assignments"],
      });
    },
  });

  return (
    <Modal
      title={`${position.code} — ${t("org:positions.kpiTemplate")}`}
      open
      onCancel={onClose}
      footer={null}
      width={640}
    >
      <Table
        size="small"
        rowKey="id"
        loading={assignmentsQuery.isLoading}
        dataSource={assignmentsQuery.data ?? []}
        pagination={false}
        columns={[
          {
            title: t("kpiTemplates:title"),
            key: "template",
            render: (_: unknown, a: { template_id: number }) => templateName(a.template_id),
          },
          { title: t("org:rates.from"), dataIndex: "effective_from", render: (v: string) => <Ltr>{v}</Ltr> },
          {
            title: t("org:rates.to"),
            dataIndex: "effective_to",
            render: (v: string | null) => <Ltr>{v ?? t("org:rates.openEnded")}</Ltr>,
          },
        ]}
        style={{ marginBottom: 24 }}
      />

      <Can permission="ASSIGN_KPI_TEMPLATES">
        <Typography.Title level={5}>{t("org:positions.assignKpiTemplate")}</Typography.Title>
        <Form
          layout="vertical"
          onFinish={(values: {
            template_id: number;
            effective_from: dayjs.Dayjs;
            effective_to?: dayjs.Dayjs;
          }) =>
            createMutation.mutate({
              template_id: values.template_id,
              effective_from: values.effective_from.format("YYYY-MM-DD"),
              effective_to: values.effective_to ? values.effective_to.format("YYYY-MM-DD") : undefined,
            })
          }
        >
          <Space wrap align="start">
            <Form.Item name="template_id" label={t("kpiTemplates:title")} rules={[{ required: true }]}>
              <Select
                style={{ minWidth: 220 }}
                options={(templatesQuery.data ?? []).map((tpl) => ({
                  value: tpl.id,
                  label: `${tpl.code} — ${localized(tpl.name_en, tpl.name_ar)}`,
                }))}
              />
            </Form.Item>
            <Form.Item name="effective_from" label={t("org:rates.from")} rules={[{ required: true }]}>
              <DatePicker />
            </Form.Item>
            <Form.Item name="effective_to" label={t("org:rates.to")}>
              <DatePicker />
            </Form.Item>
          </Space>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={createMutation.isPending}>
              {t("common:common.create")}
            </Button>
          </Form.Item>
          {createMutation.isError && (
            <Typography.Text type="danger">{t("org:positions.assignmentOverlapError")}</Typography.Text>
          )}
        </Form>
      </Can>
    </Modal>
  );
}

export default OrgPage;
