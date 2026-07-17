import { Button, Card, Form, Input, Typography } from "antd";
import { useTranslation } from "react-i18next";

interface LoginFormValues {
  staffNo: string;
  password: string;
}

export function LoginPage() {
  const { t } = useTranslation();

  const onFinish = (values: LoginFormValues) => {
    // Wired up to POST /auth/login in Phase 1.
    console.info("login submitted", values);
  };

  return (
    <div style={{ display: "flex", justifyContent: "center", paddingTop: 80 }}>
      <Card style={{ width: 360 }}>
        <Typography.Title level={3} style={{ textAlign: "center" }}>
          {t("app.name")}
        </Typography.Title>
        <Form layout="vertical" onFinish={onFinish}>
          <Form.Item
            name="staffNo"
            label={t("auth.staffNo")}
            rules={[{ required: true }]}
          >
            <Input autoFocus />
          </Form.Item>
          <Form.Item
            name="password"
            label={t("auth.password")}
            rules={[{ required: true }]}
          >
            <Input.Password />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" block>
              {t("auth.login")}
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}

export default LoginPage;
