export const TOKEN_KEY = "brasaland.access_token";

export type FieldErrors = Record<string, string>;

export class ApiError extends Error {
  constructor(message: string, public status: number, public fields: FieldErrors = {}) {
    super(message);
  }
}

export function getToken(): string | null {
  return window.localStorage.getItem(TOKEN_KEY);
}

export function endSession(): void {
  window.localStorage.removeItem(TOKEN_KEY);
  window.location.replace("/login");
}

export async function sessionFetch(url: string, init: RequestInit = {}, protectedCall = true): Promise<Response> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (protectedCall) {
    const token = getToken();
    if (!token) {
      endSession();
      throw new ApiError("Please sign in to continue.", 401);
    }
    headers.set("Authorization", `Bearer ${token}`);
  }
  const response = await fetch(url, { ...init, headers, cache: "no-store" });
  if (protectedCall && response.status === 401) {
    endSession();
    throw new ApiError("Your session has expired. Please sign in again.", 401);
  }
  return response;
}

export async function apiRequest<T>(url: string, init: RequestInit = {}, protectedCall = true): Promise<T> {
  const response = await sessionFetch(url, init, protectedCall);
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const fields: FieldErrors = {};
    if (Array.isArray(payload.detail)) {
      for (const error of payload.detail) {
        const field = error.loc?.at(-1);
        if (field) fields[field] = error.msg;
      }
    }
    if (response.status === 409) fields.email = payload.detail;
    const message = typeof payload.detail === "string"
      ? payload.detail : "Please check the highlighted fields and try again.";
    throw new ApiError(message, response.status, fields);
  }
  return response.status === 204 ? undefined as T : response.json();
}