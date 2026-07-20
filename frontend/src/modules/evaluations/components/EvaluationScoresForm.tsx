import { useMemo, useState } from "react";
import { Button, Input, InputNumber, Progress, Rate, Space, Table, Tag, Tooltip, Typography, message } from "antd";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { updateEvaluation } from "@/modules/evaluations/api/evaluationsApi";
import { evaluationStatusColor } from "@/modules/evaluations/statusColor";
import type { EvaluationOut, EvaluationScoreOut } from "@/modules/evaluations/types";
import { useLocalizedField } from "@/shared/hooks/useLocalizedField";
import { Ltr } from "@/shared/ui/Ltr";

interface Draft {
  rawInput: number | null;
  remarks: string | null;
}

function computeAwarded(score: EvaluationScoreOut, rawInput: number | null): number {
  if (rawInput === null) return 0;
  if (score.input_mode === "scale_1_5") {
    return (rawInput / 5) * score.max_marks;
  }
  if (!score.allow_negative && rawInput < 0) return 0;
  return rawInput;
}

export function EvaluationScoresForm({
  evaluation,
  editable,
  onSaved,
}: {
  evaluation: EvaluationOut;
  editable: boolean;
  onSaved: (updated: EvaluationOut) => void;
}) {
  const { t } = useTranslation(["common", "evaluations"]);
  const localized = useLocalizedField();
  const queryClient = useQueryClient();

  const sortedScores = useMemo(() => evaluation.scores, [evaluation.scores]);
  const [drafts, setDrafts] = useState<Record<number, Draft>>(() =>
    Object.fromEntries(
      sortedScores.map((s) => [
        s.criterion_id,
        { rawInput: s.raw_input !== null ? Number(s.raw_input) : null, remarks: s.remarks },
      ]),
    ),
  );

  const total = sortedScores.reduce(
    (sum, s) => sum + computeAwarded(s, drafts[s.criterion_id]?.rawInput ?? null),
    0,
  );
  const maxTotal = sortedScores.reduce((sum, s) => sum + s.max_marks, 0);
  const pct = maxTotal > 0 ? Math.max(0, Math.round((total / maxTotal) * 100)) : 0;

  const saveMutation = useMutation({
    mutationFn: () =>
      updateEvaluation(evaluation.id, {
        row_version: evaluation.row_version,
        scores: sortedScores.map((s) => ({
          criterion_id: s.criterion_id,
          raw_input: drafts[s.criterion_id]?.rawInput ?? null,
          remarks: drafts[s.criterion_id]?.remarks ?? null,
        })),
      }),
    onSuccess: (updated) => {
      void message.success(t("evaluations:scoresSaved"));
      void queryClient.invalidateQueries({ queryKey: ["evaluations"] });
      onSaved(updated);
    },
    onError: (err: unknown) => {
      const status = (err as { response?: { status?: number } }).response?.status;
      if (status === 409) {
        void message.error(t("evaluations:errors.rowVersionConflict"));
      } else {
        void message.error(t("evaluations:errors.saveFailed"));
      }
    },
  });

  return (
    <div>
      <Space align="center" style={{ marginBottom: 12 }}>
        <Progress type="circle" size={56} percent={pct} status={pct === 100 ? "success" : "active"} />
        <Typography.Text strong>
          {t("evaluations:totalOutOf", { total: total.toFixed(1), max: maxTotal })}
        </Typography.Text>
      </Space>

      <Table<EvaluationScoreOut>
        rowKey="criterion_id"
        size="small"
        pagination={false}
        dataSource={sortedScores}
        columns={[
          {
            title: t("evaluations:criterion"),
            key: "name",
            render: (_: unknown, s: EvaluationScoreOut) => (
              <Space direction="vertical" size={0}>
                <bdi>{localized(s.name_en, s.name_ar)}</bdi>
                {(s.guidance_en ?? s.guidance_ar) && (
                  <Tooltip title={<bdi>{localized(s.guidance_en, s.guidance_ar ?? "")}</bdi>}>
                    <Typography.Text type="secondary" style={{ fontSize: 12, cursor: "help" }}>
                      {t("evaluations:guidance")}
                    </Typography.Text>
                  </Tooltip>
                )}
              </Space>
            ),
          },
          {
            title: t("evaluations:maxMarks"),
            dataIndex: "max_marks",
            width: 90,
            render: (v: number) => <Ltr>{v}</Ltr>,
          },
          {
            title: t("evaluations:score"),
            key: "input",
            width: 200,
            render: (_: unknown, s: EvaluationScoreOut) => {
              const draft = drafts[s.criterion_id];
              if (!editable) {
                return <Ltr>{s.awarded_marks ?? "—"}</Ltr>;
              }
              if (s.input_mode === "scale_1_5") {
                return (
                  <Rate
                    count={5}
                    value={draft?.rawInput ?? 0}
                    onChange={(v) =>
                      setDrafts((prev) => ({ ...prev, [s.criterion_id]: { ...prev[s.criterion_id], rawInput: v } }))
                    }
                  />
                );
              }
              return (
                <InputNumber
                  value={draft?.rawInput ?? undefined}
                  min={s.allow_negative ? -s.max_marks : 0}
                  max={s.max_marks}
                  onChange={(v) =>
                    setDrafts((prev) => ({
                      ...prev,
                      [s.criterion_id]: { ...prev[s.criterion_id], rawInput: v },
                    }))
                  }
                />
              );
            },
          },
          {
            title: t("evaluations:suggested"),
            key: "suggested",
            width: 130,
            render: (_: unknown, s: EvaluationScoreOut) => {
              if (s.auto_suggested_marks === null) return "—";
              const suggested = Number(s.auto_suggested_marks);
              const draft = drafts[s.criterion_id];
              const applied = draft?.rawInput === suggested;
              return (
                <Space>
                  <Ltr>{s.auto_suggested_marks}</Ltr>
                  {editable && !applied && (
                    <Button
                      size="small"
                      onClick={() =>
                        setDrafts((prev) => ({
                          ...prev,
                          [s.criterion_id]: { ...prev[s.criterion_id], rawInput: suggested },
                        }))
                      }
                    >
                      {t("evaluations:apply")}
                    </Button>
                  )}
                </Space>
              );
            },
          },
          {
            title: t("evaluations:remarks"),
            key: "remarks",
            render: (_: unknown, s: EvaluationScoreOut) =>
              editable ? (
                <Input
                  value={drafts[s.criterion_id]?.remarks ?? ""}
                  onChange={(e) =>
                    setDrafts((prev) => ({
                      ...prev,
                      [s.criterion_id]: { ...prev[s.criterion_id], remarks: e.target.value },
                    }))
                  }
                />
              ) : (
                s.remarks ?? "—"
              ),
          },
        ]}
      />

      {editable && (
        <Button
          type="primary"
          style={{ marginTop: 12 }}
          loading={saveMutation.isPending}
          onClick={() => saveMutation.mutate()}
        >
          {t("common:common.save")}
        </Button>
      )}
    </div>
  );
}

export function EvaluationStatusTag({ status }: { status: string }) {
  const { t } = useTranslation("evaluations");
  return <Tag color={evaluationStatusColor(status)}>{t(`status.${status}`)}</Tag>;
}
