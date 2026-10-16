"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useSyncExternalStore, type FormEvent } from "react";
import { register, signIn } from "@/services/authApi";
import { ApiError, type FieldErrors } from "@/services/session";
import { useHydrated } from "@/hooks/useHydrated";

const subscribeToLocation = () => () => undefined;
const resetSuccessSnapshot = () => typeof window !== "undefined"
  && new URLSearchParams(window.location.search).get("password-reset") === "success";
const serverResetSuccessSnapshot = () => false;

export function AuthForm({ registration = false }: { registration?: boolean }) {
  const router = useRouter();
  const hydrated = useHydrated();
  const resetSuccess = useSyncExternalStore(subscribeToLocation, resetSuccessSnapshot, serverResetSuccessSnapshot);
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
    const value = (key: string) => String(values.get(key) ?? "");
    const password = value("password");
    if (registration && new TextEncoder().encode(password).length > 72) {
      setFields({ password: "Password must not exceed 72 UTF-8 bytes." });
      setBusy(false);
      return;
    }
    try {
      if (registration) {
        await register(value("email"), password, {
          name: value("name"), phone: value("phone"), address: value("address"),
        });
      } else {
        await signIn(value("email"), password);
      }
      router.replace("/");
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Unable to connect. Please try again.");
      if (failure instanceof ApiError) setFields(failure.fields);
    } finally {
      setBusy(false);
    }
  }

  const input = (name: string, label: string, type = "text", maxLength?: number) => <div className="auth-field" key={name}>
    <label htmlFor={name}>{label}</label>
    <input id={name} name={name} type={type} required={name === "email" || name === "password"}
      minLength={registration && name === "password" ? 8 : undefined} maxLength={maxLength}
      autoComplete={name === "password" ? registration ? "new-password" : "current-password" : name === "phone" ? "tel" : name === "address" ? "street-address" : name}
      aria-invalid={Boolean(fields[name])} aria-describedby={fields[name] ? `${name}-error` : undefined} />
    {fields[name] && <p className="auth-field-error" id={`${name}-error`}>{fields[name]}</p>}
  </div>;

  return <main className="auth-page">
    <section className="auth-content">
      <p className="auth-brand">Brasaland / People and Culture</p>
      <h1>{registration ? "Create account" : "Log in"}</h1>
      {resetSuccess && <p className="auth-success" role="status">Your password was reset. You can sign in with your new password.</p>}
      <form method="post" onSubmit={submit} aria-busy={busy}>
        <fieldset disabled={busy || !hydrated}>
          {input("email", "Email", "email")}
          {input("password", "Password", "password", registration ? 72 : undefined)}
          {registration && <>{input("name", "Name (optional)", "text", 200)}{input("phone", "Phone (optional)", "tel", 50)}{input("address", "Address (optional)", "text", 500)}</>}
          {error && <p className="auth-error" role="alert">{error}</p>}
          <button className="auth-button" type="submit">{busy ? "Please wait..." : registration ? "Create account" : "Log in"}</button>
        </fieldset>
      </form>
      <Link className="auth-link" href={registration ? "/login" : "/register"}>{registration ? "Already registered? Log in" : "Create an account"}</Link>
      {!registration && <Link className="auth-link" href="/forgot-password">Forgot your password?</Link>}
    </section>
  </main>;
}