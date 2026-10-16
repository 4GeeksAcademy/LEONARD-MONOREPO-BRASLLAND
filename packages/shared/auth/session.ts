export const TOKEN_KEY = "brasaland.access_token";

export type FieldErrors = Record<string, string>;

export class ApiError extends Error {
  constructor(message: string, public status: number, public fields: FieldErrors = {}) {
    super(message);
  }
}

function publicErrorMessage(status: number): string {
  if (status === 400) return "We couldn't process that request. Please review your information and try again.";
  if (status === 401) return "Your email or password is incorrect. Please try again.";
  if (status === 403) return "You don't have permission to complete this action.";
  if (status === 404) return "We couldn't find that information. Refresh and try again.";
  if (status === 409) return "An account with this email already exists.";
  if (status === 422) return "Please review the highlighted fields and try again.";
  if (status === 429) return "Too many attempts. Please wait a moment and try again.";
  return "The service is temporarily unavailable. Please try again.";
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
  let response: Response;
  try {
    response = await sessionFetch(url, init, protectedCall);
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError("Unable to connect to the service. Please check your connection and try again.", 0);
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: unknown } | null;
    const fields: FieldErrors = {};
    if (Array.isArray(payload?.detail)) {
      for (const issue of payload.detail) {
        if (typeof issue !== "object" || issue === null) continue;
        const location = (issue as { loc?: unknown }).loc;
        const field = Array.isArray(location) ? location.at(-1) : undefined;
        if (typeof field === "string") fields[field] = "Please check this field and try again.";
      }
    }
    if (response.status === 409) fields.email = "An account with this email already exists.";
    throw new ApiError(publicErrorMessage(response.status), response.status, fields);
  }
  if (response.status === 204) return undefined as T;
  try {
    return await response.json();
  } catch {
    throw new ApiError("The service returned an unreadable response. Please try again.", response.status);
  }
}