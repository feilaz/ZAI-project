import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { ApiError, changePassword, login, logout } from "../api";
import type { LoginResponse } from "../types";

export default function AdminAccount() {
  const [session, setSession] = useState<LoginResponse | null>(null);
  const [form, setForm] = useState<"login" | "password" | null>(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  function expireSession() {
    setSession(null);
    setForm("login");
    setPassword("");
    setNewPassword("");
    setMessage("");
    setError("Session expired. Please log in again.");
  }

  useEffect(() => {
    if (!session) return;
    const timer = window.setTimeout(expireSession, session.expiresIn * 1000);
    return () => window.clearTimeout(timer);
  }, [session]);

  function showForm(nextForm: "login" | "password" | null) {
    setForm(nextForm);
    setPassword("");
    setNewPassword("");
    setError("");
    setMessage("");
  }

  function showError(reason: unknown) {
    if (session && reason instanceof ApiError && reason.status === 401) {
      expireSession();
    } else {
      setError(reason instanceof Error ? reason.message : "Request failed.");
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    try {
      if (session) {
        await changePassword(session.accessToken, password, newPassword);
        setMessage("Password changed.");
      } else {
        setSession(await login(username, password));
      }
      setForm(null);
      setPassword("");
      setNewPassword("");
    } catch (reason) {
      showError(reason);
    } finally {
      setBusy(false);
    }
  }

  async function signOut() {
    if (!session) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await logout(session.accessToken);
      setSession(null);
      showForm(null);
      setMessage("Logged out.");
    } catch (reason) {
      showError(reason);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="admin-account">
      {session ? (
        <div className="account-actions">
          <span>Logged in as {username}</span>
          <button
            disabled={busy}
            onClick={() => showForm(form ? null : "password")}
          >
            Change password
          </button>
          <button disabled={busy} onClick={signOut}>
            Log out
          </button>
        </div>
      ) : (
        <button disabled={busy} onClick={() => showForm(form ? null : "login")}>
          Log in
        </button>
      )}

      {form && (
        <form onSubmit={submit}>
          <h2>{session ? "Change password" : "Log in"}</h2>
          <div className="account-fields">
            {!session && (
              <label>
                Username
                <input
                  name="username"
                  autoComplete="username"
                  required
                  disabled={busy}
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                />
              </label>
            )}
            <label>
              {session ? "Current password" : "Password"}
              <input
                name="password"
                type="password"
                autoComplete="current-password"
                required
                disabled={busy}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </label>
            {session && (
              <label>
                New password
                <input
                  name="newPassword"
                  type="password"
                  autoComplete="new-password"
                  required
                  minLength={8}
                  disabled={busy}
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.target.value)}
                />
              </label>
            )}
            <button type="submit" disabled={busy}>
              {session ? "Save password" : "Sign in"}
            </button>
          </div>
        </form>
      )}
      {busy && <p role="status">Please wait…</p>}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {message && <p role="status">{message}</p>}
    </div>
  );
}
