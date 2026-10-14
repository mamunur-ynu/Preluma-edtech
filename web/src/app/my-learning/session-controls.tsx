"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

export function SignInForm() {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  async function signIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) return;
    setPending(true);
    setError("");
    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
        credentials: "same-origin",
        cache: "no-store",
      });
      if (!response.ok) {
        setPassword("");
        setError(response.status === 401 ? "The username or password was not accepted." :
          "Sign-in is temporarily unavailable. Please try again later.");
        return;
      }
      setUsername("");
      setPassword("");
      router.refresh();
    } catch {
      setPassword("");
      setError("Sign-in is temporarily unavailable. Please try again later.");
    } finally {
      setPending(false);
    }
  }

  return (
    <form className="session-form" onSubmit={signIn}>
      <h2>Sign in to continue</h2>
      <p>Use your existing Preluma student account.</p>
      <label htmlFor="preluma-username">Username</label>
      <input id="preluma-username" name="username" autoComplete="username" required maxLength={32}
        value={username} onChange={(event) => setUsername(event.target.value)} />
      <label htmlFor="preluma-password">Password</label>
      <input id="preluma-password" name="password" type="password" autoComplete="current-password" required maxLength={512}
        value={password} onChange={(event) => setPassword(event.target.value)} />
      {error && <p className="form-error" role="alert">{error}</p>}
      <button className="button" type="submit" disabled={pending}>
        {pending ? "Signing in…" : "Sign in"}
      </button>
    </form>
  );
}

export function SignOutButton() {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  async function signOut() {
    if (pending) return;
    setPending(true);
    setError("");
    try {
      const csrfResponse = await fetch("/api/auth/csrf", { credentials: "same-origin", cache: "no-store" });
      if (!csrfResponse.ok) throw new Error("CSRF unavailable");
      const data: unknown = await csrfResponse.json();
      if (typeof data !== "object" || data === null ||
          typeof (data as { csrf_token?: unknown }).csrf_token !== "string")
        throw new Error("Invalid CSRF response");
      const response = await fetch("/api/auth/logout", {
        method: "POST",
        headers: { "X-Preluma-CSRF": (data as { csrf_token: string }).csrf_token },
        credentials: "same-origin",
        cache: "no-store",
      });
      if (!response.ok) throw new Error("Sign-out unavailable");
      router.refresh();
    } catch {
      setError("Could not sign out. Please try again.");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="session-actions">
      <button className="secondary-button" type="button" onClick={signOut} disabled={pending}>
        {pending ? "Signing out…" : "Sign out"}
      </button>
      {error && <p className="form-error" role="alert">{error}</p>}
    </div>
  );
}
