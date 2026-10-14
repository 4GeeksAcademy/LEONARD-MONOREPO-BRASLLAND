"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useSyncExternalStore, type FormEvent } from "react";
import { useHydrated } from "@/hooks/useHydrated";
import { changePassword, requestPasswordReset, resetPassword } from "@/services/authApi";
import { ApiError, type FieldErrors } from "@/services/session";

const subscribeToLocation = () => () => undefined;
const resetTokenSnapshot = () => typeof window !== "undefined" && new URLSearchParams(window.location.search).has("token");
const serverResetTokenSnapshot = () => false;

export function ForgotPasswordForm() {
  const hydrated = useHydrated();
  const [busy, setBusy] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy || submitted) return;
    setBusy(true);
    const email = String(new FormData(event.currentTarget).get("email") ?? "");
    await requestPasswordReset(email).catch(() => undefined);
    setSubmitted(true);
    setBusy(false);
  }

  return <main className="auth-page"><section className="auth-content">
    <p className="auth-brand">Brasaland / Account recovery</p>
    <h1>Forgot your password?</h1>
    {submitted && <p className="auth-success" role="status">If that address is registered, you&apos;ll receive a reset link shortly.</p>}
    <form method="post" onSubmit={submit} aria-busy={busy}>
      <fieldset disabled={busy || submitted || !hydrated}>
        <div className="auth-field">
          <label htmlFor="email">Email</label>
          <input id="email" name="email" type="email" autoComplete="email" required />
        </div>
        <button className="auth-button" type="submit">{submitted ? "Request sent" : busy ? "Sending..." : "Send reset link"}</button>
      </fieldset>
    </form>
    <Link className="auth-link" href="/login">Back to log in</Link>
  </section></main>;
}

export function ResetPasswordForm() {
  const router = useRouter();
  const hydrated = useHydrated();
  const hasResetToken = useSyncExternalStore(subscribeToLocation, resetTokenSnapshot, serverResetTokenSnapshot);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [fields, setFields] = useState<FieldErrors>({});

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError("");
    setFields({});
    const values = new FormData(event.currentTarget);
    const newPassword = String(values.get("new_password") ?? "");
    const confirmation = String(values.get("confirm_password") ?? "");
    if (newPassword !== confirmation) {
      setFields({ confirm_password: "Passwords do not match." });
      setBusy(false);
      return;
    }
    if (new TextEncoder().encode(newPassword).length > 72) {
      setFields({ new_password: "Password must not exceed 72 UTF-8 bytes." });
      setBusy(false);
      return;
    }
    const token = new URLSearchParams(window.location.search).get("token");
    if (!token) {
      setError("This password reset link is missing its token.");
      setBusy(false);
      return;
    }
    try {
      await resetPassword(token, newPassword);
      router.replace("/login?password-reset=success");
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Unable to reset your password.");
      if (failure instanceof ApiError) setFields(failure.fields);
      setBusy(false);
    }
  }

  return <main className="auth-page"><section className="auth-content">
    <p className="auth-brand">Brasaland / Account recovery</p>
    <h1>Choose a new password</h1>
    <form method="post" onSubmit={submit} aria-busy={busy}>
      <fieldset disabled={busy || !hydrated}>
        <div className="auth-field">
          <label htmlFor="new_password">New password</label>
          <input id="new_password" name="new_password" type="password" autoComplete="new-password" minLength={8} maxLength={72} required
            aria-invalid={Boolean(fields.new_password)} aria-describedby={fields.new_password ? "new_password-error" : undefined} />
          {fields.new_password && <p className="auth-field-error" id="new_password-error">{fields.new_password}</p>}
        </div>
        <div className="auth-field">
          <label htmlFor="confirm_password">Confirm new password</label>
          <input id="confirm_password" name="confirm_password" type="password" autoComplete="new-password" minLength={8} maxLength={72} required
            aria-invalid={Boolean(fields.confirm_password)} aria-describedby={fields.confirm_password ? "confirm_password-error" : undefined} />
          {fields.confirm_password && <p className="auth-field-error" id="confirm_password-error">{fields.confirm_password}</p>}
        </div>
        {error && <p className="auth-error" role="alert">{error}</p>}
        <button className="auth-button" type="submit">{busy ? "Updating..." : "Reset password"}</button>
      </fieldset>
    </form>
    {(error || !hasResetToken) && <Link className="auth-link" href="/forgot-password">Request a new reset link</Link>}
  </section></main>;
}

export function ChangePasswordForm() {
  const hydrated = useHydrated();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [fields, setFields] = useState<FieldErrors>({});

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setMessage("");
    setError("");
    setFields({});
    const form = event.currentTarget;
    const values = new FormData(form);
    const currentPassword = String(values.get("current_password") ?? "");
    const newPassword = String(values.get("new_password") ?? "");
    const confirmation = String(values.get("confirm_password") ?? "");
    if (newPassword !== confirmation) {
      setFields({ confirm_password: "Passwords do not match." });
      setBusy(false);
      return;
    }
    if (new TextEncoder().encode(newPassword).length > 72) {
      setFields({ new_password: "Password must not exceed 72 UTF-8 bytes." });
      setBusy(false);
      return;
    }
    try {
      await changePassword(currentPassword, newPassword);
      form.reset();
      setMessage("Password changed successfully.");
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Unable to change your password.");
      if (failure instanceof ApiError) setFields(failure.fields);
    } finally {
      setBusy(false);
    }
  }

  return <main className="auth-page"><section className="auth-content">
    <p className="auth-brand">Brasaland / Account</p>
    <h1>Change password</h1>
    <form method="post" onSubmit={submit} aria-busy={busy}>
      <fieldset disabled={busy || !hydrated}>
        <div className="auth-field">
          <label htmlFor="current_password">Current password</label>
          <input id="current_password" name="current_password" type="password" autoComplete="current-password" maxLength={72} required />
        </div>
        <div className="auth-field">
          <label htmlFor="new_password">New password</label>
          <input id="new_password" name="new_password" type="password" autoComplete="new-password" minLength={8} maxLength={72} required
            aria-invalid={Boolean(fields.new_password)} aria-describedby={fields.new_password ? "new_password-error" : undefined} />
          {fields.new_password && <p className="auth-field-error" id="new_password-error">{fields.new_password}</p>}
        </div>
        <div className="auth-field">
          <label htmlFor="confirm_password">Confirm new password</label>
          <input id="confirm_password" name="confirm_password" type="password" autoComplete="new-password" minLength={8} maxLength={72} required
            aria-invalid={Boolean(fields.confirm_password)} aria-describedby={fields.confirm_password ? "confirm_password-error" : undefined} />
          {fields.confirm_password && <p className="auth-field-error" id="confirm_password-error">{fields.confirm_password}</p>}
        </div>
        {error && <p className="auth-error" role="alert">{error}</p>}
        {message && <p className="auth-success" role="status">{message}</p>}
        <button className="auth-button" type="submit">{busy ? "Updating..." : "Change password"}</button>
      </fieldset>
    </form>
  </section></main>;
}