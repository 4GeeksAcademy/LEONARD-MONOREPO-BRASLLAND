"use client";

import { useState, type FormEvent } from "react";
import { useCurrentUser } from "@/components/auth/AuthBoundary";
import { updateProfile } from "@/services/authApi";
import { ApiError, type FieldErrors } from "@/services/session";

export default function ProfilePage() {
  const user = useCurrentUser();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [fields, setFields] = useState<FieldErrors>({});
  if (!user) return null;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setMessage("");
    setError("");
    setFields({});
    const values = new FormData(event.currentTarget);
    try {
      await updateProfile({ name: String(values.get("name")), phone: String(values.get("phone")), address: String(values.get("address")) });
      setMessage("Profile saved.");
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Unable to save profile.");
      if (failure instanceof ApiError) setFields(failure.fields);
    } finally {
      setBusy(false);
    }
  }

  return <main className="auth-page profile-page"><section className="auth-content">
    <p className="auth-brand">Brasaland / Account</p>
    <h1>My profile</h1>
    <div className="auth-field"><label htmlFor="email">Email</label><textarea id="email" value={user.email} readOnly rows={2} /></div>
    <form onSubmit={submit} aria-busy={busy}><fieldset disabled={busy}>
      {(["name", "phone", "address"] as const).map(name => <div className="auth-field" key={name}>
        <label htmlFor={name}>{name === "name" ? "Name" : name === "phone" ? "Phone" : "Address"}</label>
        <input id={name} name={name} type={name === "phone" ? "tel" : "text"} defaultValue={user.profile[name]}
          maxLength={name === "name" ? 200 : name === "phone" ? 50 : 500}
          autoComplete={name === "phone" ? "tel" : name === "address" ? "street-address" : "name"}
          aria-invalid={Boolean(fields[name])} aria-describedby={fields[name] ? `${name}-error` : undefined} />
        {fields[name] && <p className="auth-field-error" id={`${name}-error`}>{fields[name]}</p>}
      </div>)}
      {error && <p className="auth-error" role="alert">{error}</p>}
      {message && <p role="status" className="auth-success">{message}</p>}
      <button className="auth-button" type="submit">{busy ? "Saving..." : "Save profile"}</button>
    </fieldset></form>
  </section></main>;
}