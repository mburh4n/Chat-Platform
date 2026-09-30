const DEFAULT_ERROR = "Something went wrong. Please try again.";

// Pydantic adds "Value error, " before messages from our custom validators
function cleanMessage(message) {
  return String(message).replace(/^Value error, /, "");
}

/**
 * One friendly sentence for any API error, e.g. for a message above a form.
 */
export function getErrorMessage(error, fallback = DEFAULT_ERROR) {
  // No response at all: server down, network problem, timeout, or CORS blocked
  if (!error.response) {
    if (error.code === "ECONNABORTED") {
      return "The server took too long to respond. Please try again.";
    }
    return "Cannot reach the server. Please check your connection and try again.";
  }

  const detail = error.response.data?.detail;

  // Our backend's errors: {"detail": "Invalid email or password."}
  if (typeof detail === "string") {
    return detail;
  }

  // Validation errors (422): shown next to each field instead
  if (Array.isArray(detail) && detail.length > 0) {
    return "Please correct the highlighted fields.";
  }

  return fallback;
}

/**
 * Field-by-field messages from a 422 validation error,
 * e.g. { email: "...", password: "..." }. Empty object otherwise.
 */
export function getFieldErrors(error) {
  const detail = error.response?.data?.detail;
  const fieldErrors = {};

  if (!Array.isArray(detail)) {
    return fieldErrors;
  }

  for (const item of detail) {
    // loc looks like ["body", "email"]: the last part is the field name
    const field = item.loc?.[item.loc.length - 1];
    if (typeof field === "string" && !fieldErrors[field]) {
      fieldErrors[field] = cleanMessage(item.msg);
    }
  }

  return fieldErrors;
}
