import type { CSSProperties } from "react";

/**
 * antd Input/Input.Password render an affix wrapper when a suffix icon is present
 * (e.g. the password-visibility toggle) — `style` on the component lands on that
 * wrapper, not the actual <input>, so RTL page direction still bidi-reorders Latin
 * text typed inside it (e.g. a trailing "!" visually jumps to the front). The
 * `styles.input` semantic slot targets the real input element.
 */
export const LTR_INPUT_STYLES: { input: CSSProperties } = {
  input: { direction: "ltr", textAlign: "left" },
};
