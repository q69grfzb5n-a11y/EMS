import type { CSSProperties, PropsWithChildren } from "react";

const STYLE: CSSProperties = { display: "inline-block", fontVariantNumeric: "tabular-nums" };

/** Isolates staff numbers / dates / money inside RTL rows so digits don't bidi-reorder. */
export function Ltr({ children }: PropsWithChildren) {
  return (
    <span dir="ltr" style={STYLE}>
      {children}
    </span>
  );
}
