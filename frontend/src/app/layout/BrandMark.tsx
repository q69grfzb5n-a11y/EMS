import { BRAND_COLOR } from "@/app/theme";

interface BrandMarkProps {
  size?: number;
}

/** The "S" monogram used as the app's brand mark (header, login screen) and
 * as the source for public/favicon.svg — keep those two in sync if this
 * changes. */
export function BrandMark({ size = 32 }: BrandMarkProps) {
  return (
    <div
      aria-hidden="true"
      style={{
        width: size,
        height: size,
        minWidth: size,
        borderRadius: size * 0.28,
        background: "#ffffff",
        color: BRAND_COLOR,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontWeight: 700,
        fontSize: size * 0.55,
        lineHeight: 1,
        userSelect: "none",
      }}
    >
      S
    </div>
  );
}
