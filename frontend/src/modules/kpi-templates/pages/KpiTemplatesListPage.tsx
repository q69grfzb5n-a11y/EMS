import { useState } from "react";
import { Button, Form, Input, Modal, Space, Table, Tag, Typography } from "antd";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { createTemplate, listTemplates } from "@/modules/kpi-templates/api/kpiTemplatesApi";
import type { KpiTemplateOut } from "@/modules/kpi-templates/types";
import { Can } from "@/shared/auth/Can";
import { useLocalizedField } from "@/shared/hooks/useLocalizedField";
import { Ltr } from "@/shared/ui/Ltr";
import { LTR_INPUT_STYLES } from "@/shared/ui/ltrInput";

export function KpiTemplatesListPage() {
  const { t } = useTranslation(["common", "kpiTemplates"]);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const localized = useLocalizedField();
  const query = useQuery({ queryKey: ["kpi-templates"], queryFn: listTemplates });
  const [createOpen, setCreateOpen] = useState(false);

  const createMutation = useMutation({
    mutationFn: createTemplate,
    onSuccess: (template) => {
      setCreateOpen(false);
      void queryClient.invalidateQueries({ queryKey: ["kpi-templates"] });
      navigate(`/kpi-templates/${template.id}`);
    },
  });

  return (
    <div>
      <Space style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
        <Typography.Title level={3} style={{ margin: 0 }}>
          {t("kpiTemplates:title")}
        </Typography.Title>
        <Can permission="MANAGE_KPI_TEMPLATES">
          <Button type="primary" onClick={() => setCreateOpen(true)}>
            {t("kpiTemplates:create")}
          </Button>
        </Can>
      </Space>

      <Table<KpiTemplateOut>
        rowKey="id"
        loading={query.isLoading}
        dataSource={query.data ?? []}
        pagination={false}
        onRow={(record) => ({
          onClick: () => navigate(`/kpi-templates/${record.id}`),
          style: { cursor: "pointer" },
        })}
        columns={[
          { title: t("kpiTemplates:code"), dataIndex: "code", render: (v: string) => <Ltr>{v}</Ltr> },
          {
            title: t("kpiTemplates:name"),
            key: "name",
            render: (_: unknown, tpl: KpiTemplateOut) => (
              <bdi>{localized(tpl.name_en, tpl.name_ar)}</bdi>
            ),
          },
          {
            title: t("kpiTemplates:activeVersion"),
            key: "active_version",
            render: (_: unknown, tpl: KpiTemplateOut) =>
              tpl.active_version ? (
                <Space>
                  <Tag color="green">v{tpl.active_version.version_no}</Tag>
                  <Ltr>{tpl.active_version.total_marks}/100</Ltr>
                </Space>
              ) : (
                <Tag>{t("kpiTemplates:noActiveVersion")}</Tag>
              ),
          },
        ]}
      />

      <Modal
        title={t("kpiTemplates:create")}
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        footer={null}
        destroyOnHidden
      >
        <Form layout="vertical" onFinish={(values) => createMutation.mutate(values)}>
          <Form.Item name="code" label={t("kpiTemplates:code")} rules={[{ required: true }]}>
            <Input dir="ltr" styles={LTR_INPUT_STYLES} />
          </Form.Item>
          <Form.Item name="name_en" label={t("kpiTemplates:nameEn")} rules={[{ required: true }]}>
            <Input dir="ltr" styles={LTR_INPUT_STYLES} />
          </Form.Item>
          <Form.Item name="name_ar" label={t("kpiTemplates:nameAr")} rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={createMutation.isPending} block>
              {t("common:common.create")}
            </Button>
          </Form.Item>
          {createMutation.isError && (
            <Typography.Text type="danger">{t("kpiTemplates:errors.codeTaken")}</Typography.Text>
          )}
        </Form>
      </Modal>
    </div>
  );
}

export default KpiTemplatesListPage;
