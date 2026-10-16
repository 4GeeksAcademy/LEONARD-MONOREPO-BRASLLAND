import { apiRequest, TOKEN_KEY } from "./session";

export type Profile = { name: string; phone: string; address: string };
export type CurrentUser = { id: string; email: string; profile: Profile };

export const getCurrentUser = () => apiRequest<CurrentUser>("/api/backend/auth/me");
export const updateProfile = (profile: Profile) => apiRequest<Profile>("/api/backend/profiles/me", {
  method: "PUT", body: JSON.stringify(profile),
});

export const requestPasswordReset = (email: string) => apiRequest<{ message: string }>("/api/backend/auth/forgot-password", {
  method: "POST", body: JSON.stringify({ email }),
}, false);

export const resetPassword = (token: string, new_password: string) => apiRequest<{ message: string }>("/api/backend/auth/reset-password", {
  method: "POST", body: JSON.stringify({ token, new_password }),
}, false);

export const changePassword = (current_password: string, new_password: string) => apiRequest<{ message: string }>("/api/backend/auth/change-password", {
  method: "POST", body: JSON.stringify({ current_password, new_password }),
});

export async function signIn(email: string, password: string): Promise<void> {
  const result = await apiRequest<{ access_token: string }>("/api/backend/auth/login", {
    method: "POST", body: JSON.stringify({ email, password }),
  }, false);
  if (!result.access_token) throw new Error("Unable to sign in right now. Please try again.");
  window.localStorage.setItem(TOKEN_KEY, result.access_token);
}

export async function register(email: string, password: string, profile: Profile): Promise<void> {
  await apiRequest("/api/backend/users", {
    method: "POST", body: JSON.stringify({ email, password, ...profile }),
  }, false);
  try {
    await signIn(email, password);
  } catch {
    throw new Error("Your account was created, but sign-in failed. Please use the login page.");
  }
}