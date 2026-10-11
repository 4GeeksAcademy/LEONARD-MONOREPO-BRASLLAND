"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { createContext, useContext, useEffect, useState } from "react";
import { LogOut, UserRound } from "lucide-react";
import { getCurrentUser, type CurrentUser } from "@/services/authApi";
import { endSession, getToken, TOKEN_KEY } from "@/services/session";

const UserContext = createContext<CurrentUser | null>(null);
export const useCurrentUser = () => useContext(UserContext);

export function AuthBoundary({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const publicRoute = pathname === "/login" || pathname === "/register";
  const [session, setSession] = useState<{ path: string; user?: CurrentUser; error?: string }>();
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (publicRoute) return;
    let active = true;
    if (!getToken()) {
      endSession();
      return;
    }
    getCurrentUser().then(user => {
      if (active) setSession({ path: pathname, user });
    }).catch(error => {
      if (active) setSession({ path: pathname, error: error.message || "Unable to verify your session." });
    });
    const onStorage = (event: StorageEvent) => {
      if ((event.key === TOKEN_KEY || event.key === null) && !getToken()) endSession();
      else if (event.key === TOKEN_KEY) setAttempt(value => value + 1);
    };
    window.addEventListener("storage", onStorage);
    return () => {
      active = false;
      window.removeEventListener("storage", onStorage);
    };
  }, [pathname, publicRoute, attempt]);

  if (publicRoute) return children;
  if (session?.path !== pathname || !session.user) {
    return <main className="auth-status" aria-live="polite">
      <p>{session?.path === pathname && session.error ? session.error : "Verifying session..."}</p>
      {session?.error && <button className="auth-button" onClick={() => setAttempt(value => value + 1)}>Retry</button>}
    </main>;
  }
  return <UserContext.Provider value={session.user}>
    <nav className="account-nav" aria-label="Account navigation">
      <Link href="/">Talent pipeline</Link>
      <a href="/backoffice/">Incident analysis</a>
      <a href="/backoffice/suppliers/">Suppliers</a>
      <Link href="/account/profile" className="account-control"><UserRound size={16} aria-hidden="true" />My profile</Link>
      <button onClick={endSession} className="account-control" title="Log out"><LogOut size={16} aria-hidden="true" />Log out</button>
    </nav>
    {children}
  </UserContext.Provider>;
}