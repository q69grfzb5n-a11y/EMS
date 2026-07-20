import { Button, Form, Input, Modal } from "antd";
import { useTranslation } from "react-i18next";

interface ApprovalActionModalProps {
  action: "submit" | "approve" | "return" | "review";
  open: boolean;
  loading: boolean;
  requireComment?: boolean;
  onCancel: () => void;
  onConfirm: (comment?: string) => void;
}

export function ApprovalActionModal({
  action,
  open,
  loading,
  requireComment = false,
  onCancel,
  onConfirm,
}: ApprovalActionModalProps) {
  const { t } = useTranslation(["common", "approvals"]);

  return (
    <Modal title={t(`approvals:actions.${action}`)} open={open} onCancel={onCancel} footer={null} destroyOnHidden>
      <Form layout="vertical" onFinish={(values: { comment?: string }) => onConfirm(values.comment)}>
        <Form.Item
          name="comment"
          label={t("approvals:comment")}
          rules={requireComment ? [{ required: true }] : []}
        >
          <Input.TextArea rows={3} />
        </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit" loading={loading} block>
            {t(`approvals:actions.${action}`)}
          </Button>
        </Form.Item>
      </Form>
    </Modal>
  );
}
