import type { ReactNode } from "react";
import { Alert, Button, Skeleton } from "antd";
import { useTranslation } from "react-i18next";

interface QueryStateProps {
  isLoading: boolean;
  isError: boolean;
  onRetry?: () => void;
  children: ReactNode;
}

/** Standard loading/error wrapper for a page whose entire content depends on
 * one query — replaces the `if (!query.data) return null` pattern, which
 * rendered a blank page indistinguishable between "still loading" and "the
 * request failed." Use directly around a detail page's content. */
export function QueryState({ isLoading, isError, onRetry, children }: QueryStateProps) {
  const { t } = useTranslation();

  if (isLoading) {
    return <Skeleton active paragraph={{ rows: 4 }} />;
  }

  if (isError) {
    return (
      <Alert
        type="error"
        showIcon
        message={t("common.loadError")}
        action={
          onRetry ? (
            <Button size="small" onClick={onRetry}>
              {t("common.retry")}
            </Button>
          ) : undefined
        }
      />
    );
  }

  return <>{children}</>;
}
