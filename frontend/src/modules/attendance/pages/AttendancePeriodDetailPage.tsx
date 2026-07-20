import { useState } from "react";
import {
  Alert,
  Button,
  Space,
  Table,
  Tabs,
  Tag,
  Typography,
  Upload,
  message,
} from "antd";
import type { UploadProps } from "antd";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";

import {
  getPeriod,
  listImports,
  listRecords,
  lockPeriod,
  unlockPeriod,
  uploadAttendanceFile,
} from "@/modules/attendance/api/attendanceApi";
import type {
  AttendanceImportOut,
  AttendanceRecordOut,
  ImportPreviewOut,
} from "@/modules/attendance/types";
import { Can } from "@/shared/auth/Can";
import { useLocalizedField } from "@/shared/hooks/useLocalizedField";
import { Ltr } from "@/shared/ui/Ltr";

function isPreview(
  result: ImportPreviewOut | AttendanceImportOut,
): result is ImportPreviewOut {
  return "issues" in result;
}

export function AttendancePeriodDetailPage() {
  const { id } = useParams<{ id: string }>();
  const periodId = Number(id);
  const { t } = useTranslation(["common", "attendance"]);
  const localized = useLocalizedField();
  const queryClient = useQueryClient();

  const periodQuery = useQuery({
    queryKey: ["attendance", "periods", periodId],
    queryFn: () => getPeriod(periodId),
    enabled: Number.isFinite(periodId),
  });
  const recordsQuery = useQuery({
    queryKey: ["attendance", "periods", periodId, "records"],
    queryFn: () => listRecords(periodId),
    enabled: Number.isFinite(periodId),
  });
  const importsQuery = useQuery({
    queryKey: ["attendance", "periods", periodId, "imports"],
    queryFn: () => listImports(periodId),
    enabled: Number.isFinite(periodId),
  });

  const lockMutation = useMutation({
    mutationFn: () => lockPeriod(periodId),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["attendance", "periods", periodId] }),
  });
  const unlockMutation = useMutation({
    mutationFn: () => unlockPeriod(periodId),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["attendance", "periods", periodId] }),
  });

  const invalidateAfterCommit = () => {
    void queryClient.invalidateQueries({ queryKey: ["attendance", "periods", periodId, "records"] });
    void queryClient.invalidateQueries({ queryKey: ["attendance", "periods", periodId, "imports"] });
  };

  if (!periodQuery.data) return null;
  const period = periodQuery.data;
  const isLocked = period.status === "locked";

  return (
    <div>
      <Space style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
        <Typography.Title level={3} style={{ margin: 0 }}>
          <Ltr>
            {String(period.month).padStart(2, "0")}-{period.year}
          </Ltr>
        </Typography.Title>
        <Space>
          <Tag color={isLocked ? "default" : "green"}>{t(`attendance:periodStatus.${period.status}`)}</Tag>
          <Can permission="MANAGE_PERIODS">
            {isLocked ? (
              <Button loading={unlockMutation.isPending} onClick={() => unlockMutation.mutate()}>
                {t("attendance:unlock")}
              </Button>
            ) : (
              <Button loading={lockMutation.isPending} onClick={() => lockMutation.mutate()}>
                {t("attendance:lock")}
              </Button>
            )}
          </Can>
        </Space>
      </Space>

      <Can permission="MANAGE_ATTENDANCE">
        <UploadWizard periodId={periodId} disabled={isLocked} onCommitted={invalidateAfterCommit} />
      </Can>

      <Tabs
        style={{ marginTop: 24 }}
        items={[
          {
            key: "records",
            label: t("attendance:records"),
            children: (
              <Table<AttendanceRecordOut>
                rowKey="id"
                size="small"
                loading={recordsQuery.isLoading}
                dataSource={recordsQuery.data ?? []}
                pagination={{ pageSize: 50 }}
                scroll={{ x: "max-content" }}
                columns={[
                  {
                    title: t("attendance:staffNo"),
                    key: "staff_no",
                    render: (_: unknown, r: AttendanceRecordOut) => <Ltr>{r.employee.staff_no}</Ltr>,
                  },
                  {
                    title: t("attendance:employeeName"),
                    key: "name",
                    render: (_: unknown, r: AttendanceRecordOut) => (
                      <bdi>{localized(r.employee.full_name_en, r.employee.full_name_ar)}</bdi>
                    ),
                  },
                  { title: t("attendance:present"), dataIndex: "present" },
                  { title: t("attendance:offDays"), dataIndex: "off_days" },
                  { title: t("attendance:absent"), dataIndex: "absent" },
                  { title: t("attendance:leave"), dataIndex: "leave" },
                  { title: t("attendance:publicHoliday"), dataIndex: "public_holiday" },
                  {
                    title: t("attendance:overTime"),
                    dataIndex: "over_time",
                    render: (v: string) => <Ltr>{v}</Ltr>,
                  },
                  {
                    title: t("attendance:deductMin"),
                    dataIndex: "deduct_min",
                    render: (v: string) => <Ltr>{v}</Ltr>,
                  },
                ]}
              />
            ),
          },
          {
            key: "imports",
            label: t("attendance:importHistory"),
            children: (
              <Table<AttendanceImportOut>
                rowKey="id"
                size="small"
                loading={importsQuery.isLoading}
                dataSource={importsQuery.data ?? []}
                pagination={false}
                columns={[
                  { title: t("attendance:filename"), dataIndex: "original_filename" },
                  { title: t("attendance:rowCount"), dataIndex: "row_count" },
                  {
                    title: t("common:common.active"),
                    dataIndex: "status",
                    render: (v: string) => (
                      <Tag color={v === "active" ? "green" : "default"}>
                        {t(`attendance:importStatus.${v}`)}
                      </Tag>
                    ),
                  },
                  {
                    title: t("attendance:uploadedAt"),
                    dataIndex: "created_at",
                    render: (v: string) => <Ltr>{new Date(v).toLocaleString()}</Ltr>,
                  },
                ]}
              />
            ),
          },
        ]}
      />
    </div>
  );
}

function UploadWizard({
  periodId,
  disabled,
  onCommitted,
}: {
  periodId: number;
  disabled: boolean;
  onCommitted: () => void;
}) {
  const { t } = useTranslation(["common", "attendance"]);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ImportPreviewOut | null>(null);

  const previewMutation = useMutation({
    mutationFn: (f: File) => uploadAttendanceFile(periodId, f, true),
    onSuccess: (result) => {
      if (isPreview(result)) setPreview(result);
    },
  });

  const commitMutation = useMutation({
    mutationFn: (f: File) => uploadAttendanceFile(periodId, f, false),
    onSuccess: () => {
      void message.success(t("attendance:wizard.committed"));
      setFile(null);
      setPreview(null);
      onCommitted();
    },
    onError: () => void message.error(t("attendance:wizard.commitFailed")),
  });

  const uploadProps: UploadProps = {
    multiple: false,
    accept: ".xlsx",
    maxCount: 1,
    beforeUpload: (candidate) => {
      setFile(candidate);
      setPreview(null);
      return false;
    },
    onRemove: () => {
      setFile(null);
      setPreview(null);
    },
    fileList: file ? [{ uid: "1", name: file.name, status: "done" }] : [],
  };

  return (
    <div>
      <Typography.Title level={5}>{t("attendance:wizard.title")}</Typography.Title>
      {disabled ? (
        <Alert type="warning" showIcon message={t("attendance:wizard.periodLocked")} />
      ) : (
        <>
          <Upload.Dragger {...uploadProps}>
            <p>{t("attendance:wizard.dropHint")}</p>
          </Upload.Dragger>

          <Space style={{ marginTop: 12 }}>
            <Button
              disabled={!file}
              loading={previewMutation.isPending}
              onClick={() => file && previewMutation.mutate(file)}
            >
              {t("attendance:wizard.preview")}
            </Button>
            <Button
              type="primary"
              disabled={!preview || preview.has_errors || !file}
              loading={commitMutation.isPending}
              onClick={() => file && commitMutation.mutate(file)}
            >
              {t("attendance:wizard.commit")}
            </Button>
          </Space>

          {preview && (
            <div style={{ marginTop: 16 }}>
              <Alert
                type={preview.has_errors ? "error" : "success"}
                showIcon
                message={t("attendance:wizard.summary", {
                  total: preview.total_rows,
                  matched: preview.matched_count,
                  unmatched: preview.unmatched_count,
                })}
              />
              {preview.issues.length > 0 && (
                <Table
                  size="small"
                  rowKey={(r) => `${r.row_number}-${r.message}`}
                  style={{ marginTop: 12 }}
                  dataSource={preview.issues}
                  pagination={{ pageSize: 10 }}
                  columns={[
                    { title: t("attendance:wizard.row"), dataIndex: "row_number", width: 80 },
                    {
                      title: t("attendance:staffNo"),
                      dataIndex: "staff_no",
                      render: (v: string | null) => (v ? <Ltr>{v}</Ltr> : "—"),
                    },
                    {
                      title: t("attendance:wizard.severity"),
                      dataIndex: "severity",
                      render: (v: string) => (
                        <Tag color={v === "error" ? "red" : "orange"}>
                          {t(`attendance:wizard.severityValues.${v}`)}
                        </Tag>
                      ),
                    },
                    { title: t("attendance:wizard.message"), dataIndex: "message" },
                  ]}
                />
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default AttendancePeriodDetailPage;
