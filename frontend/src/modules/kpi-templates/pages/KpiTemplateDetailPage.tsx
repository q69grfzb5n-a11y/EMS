import { useEffect, useState } from "react";
import {
  Button,
  Form,
  Input,
  InputNumber,
  Popconfirm,
  Progress,
  Space,
  Switch,
  Table,
  Tabs,
  Tag,
  Typography,
  message,
} from "antd";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";

import {
  activateVersion,
  cloneVersion,
  createCriterion,
  deleteCriterion,
  getTemplate,
  listVersions,
  patchCriterion,
} from "@/modules/kpi-templates/api/kpiTemplatesApi";
import type { KpiCriterionOut, KpiTemplateVersionOut } from "@/modules/kpi-templates/types";
import { Can } from "@/shared/auth/Can";
import { useAuthStore } from "@/shared/auth/authStore";
import { hasPermission } from "@/shared/auth/permissions";
import { useLocalizedField } from "@/shared/hooks/useLocalizedField";
import { Ltr } from "@/shared/ui/Ltr";

const STATUS_COLOR: Record<string, string> = { draft: "gold", active: "green", archived: "default" };

export function KpiTemplateDetailPage() {
  const { id } = useParams<{ id: string }>();
  const templateId = Number(id);
  const { t } = useTranslation(["common", "kpiTemplates"]);
  const localized = useLocalizedField();
  const queryClient = useQueryClient();
  const canManage = useAuthStore((s) => hasPermission(s.user?.roles ?? [], "MANAGE_KPI_TEMPLATES"));

  const templateQuery = useQuery({
    queryKey: ["kpi-templates", templateId],
    queryFn: () => getTemplate(templateId),
    enabled: Number.isFinite(templateId),
  });
  const versionsQuery = useQuery({
    queryKey: ["kpi-templates", templateId, "versions"],
    queryFn: () => listVersions(templateId),
    enabled: Number.isFinite(templateId),
  });

  const [selectedVersionId, setSelectedVersionId] = useState<number | null>(null);

  useEffect(() => {
    if (selectedVersionId !== null || !versionsQuery.data?.length) return;
    const active = versionsQuery.data.find((v) => v.status === "active");
    setSelectedVersionId((active ?? versionsQuery.data[0]).id);
  }, [versionsQuery.data, selectedVersionId]);

  const invalidateVersions = () => {
    void queryClient.invalidateQueries({ queryKey: ["kpi-templates", templateId, "versions"] });
    void queryClient.invalidateQueries({ queryKey: ["kpi-templates"] });
    void queryClient.invalidateQueries({ queryKey: ["kpi-templates", templateId] });
  };

  const cloneMutation = useMutation({
    mutationFn: (sourceVersionId?: number) => cloneVersion(templateId, sourceVersionId),
    onSuccess: (newVersion) => {
      invalidateVersions();
      setSelectedVersionId(newVersion.id);
    },
  });

  if (!templateQuery.data || !versionsQuery.data) return null;
  const template = templateQuery.data;
  const versions = versionsQuery.data;
  const selectedVersion = versions.find((v) => v.id === selectedVersionId) ?? versions[0];

  return (
    <div>
      <Space style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
        <Typography.Title level={3} style={{ margin: 0 }}>
          <bdi>{localized(template.name_en, template.name_ar)}</bdi> — <Ltr>{template.code}</Ltr>
        </Typography.Title>
        <Can permission="MANAGE_KPI_TEMPLATES">
          <Button loading={cloneMutation.isPending} onClick={() => cloneMutation.mutate(selectedVersion?.id)}>
            {t("kpiTemplates:cloneVersion")}
          </Button>
        </Can>
      </Space>

      <Tabs
        activeKey={selectedVersion ? String(selectedVersion.id) : undefined}
        onChange={(key) => setSelectedVersionId(Number(key))}
        items={versions.map((v) => ({
          key: String(v.id),
          label: (
            <Space>
              <Ltr>v{v.version_no}</Ltr>
              <Tag color={STATUS_COLOR[v.status]}>{t(`kpiTemplates:status.${v.status}`)}</Tag>
            </Space>
          ),
        }))}
      />

      {selectedVersion && (
        <VersionPanel
          key={selectedVersion.id}
          version={selectedVersion}
          canManage={canManage}
          onChanged={invalidateVersions}
        />
      )}
    </div>
  );
}

function VersionPanel({
  version,
  canManage,
  onChanged,
}: {
  version: KpiTemplateVersionOut;
  canManage: boolean;
  onChanged: () => void;
}) {
  const { t } = useTranslation(["common", "kpiTemplates"]);
  const localized = useLocalizedField();
  const isDraft = version.status === "draft";
  const total = version.criteria.reduce((sum, c) => sum + c.max_marks, 0);

  const activateMutation = useMutation({
    mutationFn: () => activateVersion(version.id),
    onSuccess: () => {
      void message.success(t("kpiTemplates:activated"));
      onChanged();
    },
    onError: () => void message.error(t("kpiTemplates:errors.sumInvalid")),
  });

  const createCriterionMutation = useMutation({
    mutationFn: (values: { name_en: string; name_ar: string; max_marks: number; allow_negative?: boolean }) =>
      createCriterion(version.id, values),
    onSuccess: onChanged,
  });

  const patchMutation = useMutation({
    mutationFn: ({ id, ...payload }: { id: number; max_marks?: number; allow_negative?: boolean }) =>
      patchCriterion(id, payload),
    onSuccess: onChanged,
  });

  const deleteMutation = useMutation({
    mutationFn: (criterionId: number) => deleteCriterion(criterionId),
    onSuccess: onChanged,
  });

  return (
    <div style={{ marginTop: 16 }}>
      <Space style={{ marginBottom: 12 }}>
        <Progress
          type="circle"
          size={48}
          percent={Math.min(total, 100)}
          status={total === 100 ? "success" : "exception"}
          format={() => <Ltr>{total}</Ltr>}
        />
        <Typography.Text>{t("kpiTemplates:totalMarks", { total })}</Typography.Text>
        {isDraft && (
          <Can permission="MANAGE_KPI_TEMPLATES">
            <Button
              type="primary"
              disabled={total !== 100}
              loading={activateMutation.isPending}
              onClick={() => activateMutation.mutate()}
            >
              {t("kpiTemplates:activate")}
            </Button>
          </Can>
        )}
      </Space>

      <Table<KpiCriterionOut>
        rowKey="id"
        size="small"
        pagination={false}
        dataSource={version.criteria}
        columns={[
          {
            title: t("kpiTemplates:criterionName"),
            key: "name",
            render: (_: unknown, c: KpiCriterionOut) => (
              <div>
                <bdi>{localized(c.name_en, c.name_ar)}</bdi>
                {(c.guidance_en ?? c.guidance_ar) && (
                  <div>
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                      <bdi>{localized(c.guidance_en, c.guidance_ar ?? "")}</bdi>
                    </Typography.Text>
                  </div>
                )}
              </div>
            ),
          },
          {
            title: t("kpiTemplates:maxMarks"),
            dataIndex: "max_marks",
            width: 140,
            render: (v: number, c: KpiCriterionOut) =>
              isDraft && canManage ? (
                <InputNumber
                  min={1}
                  max={100}
                  defaultValue={v}
                  onBlur={(e) => {
                    const next = Number(e.target.value);
                    if (next && next !== v) patchMutation.mutate({ id: c.id, max_marks: next });
                  }}
                />
              ) : (
                <Ltr>{v}</Ltr>
              ),
          },
          {
            title: t("kpiTemplates:inputMode"),
            dataIndex: "input_mode",
            render: (v: string) => <Tag>{t(`kpiTemplates:inputModeValues.${v}`)}</Tag>,
          },
          {
            title: t("kpiTemplates:allowNegative"),
            dataIndex: "allow_negative",
            render: (v: boolean) => (v ? <Tag color="orange">{t("common:common.active")}</Tag> : "—"),
          },
          {
            title: t("kpiTemplates:autoSource"),
            dataIndex: "auto_source",
            render: (v: string) => (v === "none" ? "—" : <Tag color="blue">{v}</Tag>),
          },
          ...(isDraft && canManage
            ? [
                {
                  title: t("common:common.edit"),
                  key: "actions",
                  render: (_: unknown, c: KpiCriterionOut) => (
                    <Popconfirm
                      title={t("kpiTemplates:confirmDeleteCriterion")}
                      onConfirm={() => deleteMutation.mutate(c.id)}
                    >
                      <Button size="small" danger>
                        {t("kpiTemplates:deleteCriterion")}
                      </Button>
                    </Popconfirm>
                  ),
                },
              ]
            : []),
        ]}
      />

      {isDraft && canManage && (
        <div style={{ marginTop: 16 }}>
          <Typography.Title level={5}>{t("kpiTemplates:addCriterion")}</Typography.Title>
          <Form
            layout="inline"
            onFinish={(values) => createCriterionMutation.mutate(values)}
          >
            <Form.Item name="name_en" rules={[{ required: true }]}>
              <Input placeholder={t("kpiTemplates:nameEn")} style={{ direction: "ltr" }} />
            </Form.Item>
            <Form.Item name="name_ar" rules={[{ required: true }]}>
              <Input placeholder={t("kpiTemplates:nameAr")} />
            </Form.Item>
            <Form.Item name="max_marks" rules={[{ required: true }]}>
              <InputNumber min={1} max={100} placeholder={t("kpiTemplates:maxMarks")} />
            </Form.Item>
            <Form.Item name="allow_negative" valuePropName="checked">
              <Switch checkedChildren={t("kpiTemplates:allowNegative")} unCheckedChildren={t("kpiTemplates:allowNegative")} />
            </Form.Item>
            <Form.Item>
              <Button type="primary" htmlType="submit" loading={createCriterionMutation.isPending}>
                {t("common:common.create")}
              </Button>
            </Form.Item>
          </Form>
        </div>
      )}

      {!isDraft && (
        <Typography.Text type="secondary">
          {t(version.status === "active" ? "kpiTemplates:activeNotice" : "kpiTemplates:archivedNotice")}
        </Typography.Text>
      )}
    </div>
  );
}

export default KpiTemplateDetailPage;
