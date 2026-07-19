import { useMemo, useState } from "react";
import { Input, Table } from "antd";
import type { TableProps } from "antd";
import { useTranslation } from "react-i18next";

interface DataTableProps<T> extends Omit<TableProps<T>, "dataSource" | "pagination"> {
  dataSource: T[];
  /** Returns the strings to match against the search box for one row; omit to disable search. */
  searchableText?: (record: T) => string[];
  pageSize?: number;
}

/**
 * Shared list screen table: client-side search box + antd's virtual rendering so a
 * ~400-500 row roster (the real employee count) stays smooth without a dedicated
 * server pagination endpoint, which the API doesn't expose yet.
 */
export function DataTable<T extends object>({
  dataSource,
  searchableText,
  pageSize = 50,
  ...rest
}: DataTableProps<T>) {
  const { t } = useTranslation();
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    if (!search.trim() || !searchableText) {
      return dataSource;
    }
    const needle = search.trim().toLowerCase();
    return dataSource.filter((record) =>
      searchableText(record).some((field) => field.toLowerCase().includes(needle)),
    );
  }, [dataSource, search, searchableText]);

  return (
    <div>
      {searchableText && (
        <Input.Search
          allowClear
          placeholder={t("common.search")}
          style={{ maxWidth: 320, marginBottom: 12 }}
          onChange={(e) => setSearch(e.target.value)}
        />
      )}
      <Table<T>
        virtual
        scroll={{ y: 520, x: "max-content" }}
        pagination={{ pageSize, showSizeChanger: true, showTotal: (total) => t("common.totalRows", { count: total }) }}
        dataSource={filtered}
        {...rest}
      />
    </div>
  );
}
