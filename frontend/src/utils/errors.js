// The API always answers errors as {"error": {"code", "message", "details"}}.
export function errorMessage(err) {
  if (!err.response) return "Cannot reach the server. Check that the API is running and try again.";
  const e = err.response.data?.error;
  if (!e) return `Request failed (${err.response.status}).`;
  if (Array.isArray(e.details) && e.details.length) {
    return `${e.message} ${e.details.map((d) => (d.field ? `${d.field}: ${d.message}` : d.message)).join("; ")}`;
  }
  return e.message || "Something went wrong.";
}

// Map validation details to {field: message} so forms can show errors next to inputs.
export function fieldErrors(err) {
  const details = err.response?.data?.error?.details;
  const out = {};
  if (Array.isArray(details)) details.forEach((d) => d.field && (out[d.field] = d.message));
  return out;
}

export const errorCode = (err) => err.response?.data?.error?.code;
