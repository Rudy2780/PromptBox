/**
 * Shared HTTP layer.
 *
 * Authentication is an httpOnly session cookie, which page scripts cannot read
 * or attach by hand -- so every request must opt in with `credentials:
 * "include"` for the browser to send it. That is easy to forget on a new call
 * site, which is why all API modules go through here.
 *
 * State-changing requests also carry a custom header. Browsers will not attach
 * a custom header to a cross-origin request without a successful CORS
 * preflight, and the API only allows known origins through that preflight, so
 * the header is what stops another site from making authenticated writes with
 * the user's cookie. The backend enforces it in dependencies/auth.py.
 */

export const API_BASE =
  import.meta.env.VITE_API_BASE || "https://promptbox-9d83.onrender.com";

export const CSRF_HEADER = "X-Requested-With";
export const CSRF_VALUE = "PromptBox";

const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);

/**
 * Perform an API request with session credentials attached.
 * @param {string} path - Path beginning with "/", or an absolute URL.
 * @param {Object} [options]
 * @param {string} [options.method="GET"]
 * @param {Object} [options.body] - Serialised as JSON when present.
 * @param {Object} [options.headers]
 * @returns {Promise<Response>} The raw response, for the caller to interpret.
 */
export function apiFetch(path, { method = "GET", body, headers = {} } = {}) {
  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;

  const finalHeaders = { ...headers };
  if (body !== undefined) {
    finalHeaders["Content-Type"] = "application/json";
  }
  if (!SAFE_METHODS.has(method.toUpperCase())) {
    finalHeaders[CSRF_HEADER] = CSRF_VALUE;
  }

  return fetch(url, {
    method,
    credentials: "include",
    headers: finalHeaders,
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
  });
}

/**
 * Perform a JSON API request and unwrap the body, throwing on failure.
 * @param {string} path
 * @param {Object} [options] - Same shape as apiFetch, plus `errorMessage`.
 * @returns {Promise<any>} Parsed response body.
 * @throws {Error} The server's `detail`, or `errorMessage` as a fallback.
 */
export async function apiJson(path, { errorMessage = "Request failed", ...options } = {}) {
  const res = await apiFetch(path, options);

  let data = null;
  try {
    data = await res.json();
  } catch {
    data = null;
  }

  if (!res.ok) {
    throw new Error(data?.detail || errorMessage);
  }

  return data;
}
