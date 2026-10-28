const configuredBaseUrl =
  process.env.NEXT_PUBLIC_API_URL?.trim() || "http://localhost:8000";

export const API_BASE_URL = configuredBaseUrl.replace(/\/+$/, "");
export const API_PREFIX = "/api/v1";

export interface ApiErrorDetail {
  field?: string;
  message?: string;
  type?: string;
}

interface ErrorEnvelope {
  error?: {
    code?: string;
    message?: string;
    details?: ApiErrorDetail[] | unknown;
    request_id?: string;
  };
}

export class ApiError extends Error {
  status: number;
  code: string;
  details?: unknown;
  requestId?: string;

  constructor(
    status: number,
    code: string,
    message: string,
    details?: unknown,
    requestId?: string,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
    this.requestId = requestId;
  }
}

export function apiUrl(path: string) {
  return `${API_BASE_URL}${API_PREFIX}${path.startsWith("/") ? path : `/${path}`}`;
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");

  if (options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  let response: Response;
  try {
    response = await fetch(apiUrl(path), {
      ...options,
      headers,
      credentials: "include",
      cache: "no-store",
    });
  } catch {
    throw new ApiError(
      0,
      "NETWORK_ERROR",
      "Unable to reach the MIS server. Check that the backend is running.",
    );
  }

  if (!response.ok) {
    let payload: ErrorEnvelope | null = null;
    try {
      payload = (await response.json()) as ErrorEnvelope;
    } catch {
      // Non-JSON error responses still surface a useful status message.
    }
    throw new ApiError(
      response.status,
      payload?.error?.code ?? `HTTP_${response.status}`,
      payload?.error?.message ??
        (response.status === 403
          ? "You do not have permission to perform this action."
          : `Request failed with status ${response.status}.`),
      payload?.error?.details,
      payload?.error?.request_id,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    return (await response.text()) as T;
  }
  return (await response.json()) as T;
}

export function errorMessage(error: unknown, fallback = "Something went wrong.") {
  if (error instanceof ApiError) {
    if (Array.isArray(error.details) && error.details.length > 0) {
      const details = error.details as ApiErrorDetail[];
      const messages = details
        .map((detail) =>
          detail.field ? `${detail.field}: ${detail.message}` : detail.message,
        )
        .filter(Boolean);
      if (messages.length > 0) return messages.join("; ");
    }
    return error.message;
  }
  return error instanceof Error ? error.message : fallback;
}

export function isAuthError(error: unknown) {
  return (
    error instanceof ApiError &&
    (error.status === 401 ||
      error.code === "TOKEN_EXPIRED" ||
      error.code === "INVALID_TOKEN" ||
      error.code === "ACCOUNT_INACTIVE")
  );
}
