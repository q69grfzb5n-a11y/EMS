import { isAxiosError } from "axios";

const KNOWN_ERROR_CODES = new Set([
  "invalid_credentials",
  "invalid_current_password",
  "staff_no_taken",
  "account_locked",
  "login_rate_limited",
  "password_change_required",
]);

/**
 * Maps a caught error to a translation-ready error code under the "errors" key of
 * whichever namespace the caller passes to `t()`. Distinguishes "the backend said no"
 * (a real error.code from our envelope) from "the request never got a response"
 * (network_error) — collapsing both into one generic message hides real outages
 * behind a misleading "wrong password" string.
 */
export function extractApiErrorCode(err: unknown): string {
  if (isAxiosError(err)) {
    if (!err.response) {
      return "network_error";
    }
    const code: unknown = err.response.data?.error?.code;
    if (typeof code === "string" && KNOWN_ERROR_CODES.has(code)) {
      return code;
    }
  }
  return "unknown_error";
}
