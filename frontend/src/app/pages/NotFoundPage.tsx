import { Button, Result } from "antd";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

export function NotFoundPage() {
  const { t } = useTranslation();

  return (
    <Result
      status="404"
      title="404"
      subTitle={t("common.notFound.subtitle")}
      extra={
        <Link to="/">
          <Button type="primary">{t("common.notFound.backHome")}</Button>
        </Link>
      }
    />
  );
}

export default NotFoundPage;
