"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { AuthShell } from "@/components/AuthShell";
import { ApiError, login } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (!email.trim() || !password) {
      setError("Email and password are required.");
      return;
    }
    setPending(true);
    try {
      await login({ email: email.trim(), password });
      router.replace("/dashboard");
    } catch (err) {
      if (err instanceof ApiError && (err.status === 401 || err.status === 422)) {
        setError("Invalid email or password.");
      } else {
        setError("Unable to sign in. Please try again.");
      }
    } finally {
      setPending(false);
    }
  }

  return (
    <AuthShell title="Welcome back" subtitle="Sign in to continue to your company OS.">
      <form onSubmit={onSubmit} className="space-y-4">
        <div>
          <label className="forge-label" htmlFor="email">
            Email
          </label>
          <input
            id="email"
            className="forge-input"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            autoComplete="email"
          />
        </div>
        <div>
          <label className="forge-label" htmlFor="password">
            Password
          </label>
          <input
            id="password"
            className="forge-input"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
          />
        </div>
        {error ? <p className="text-sm text-red-400">{error}</p> : null}
        <button className="forge-button" type="submit" disabled={pending}>
          {pending ? "Signing in..." : "Login"}
        </button>
      </form>
      <p className="mt-6 text-center text-sm text-white/40">
        No account?{" "}
        <Link className="text-violet-300" href="/signup">
          Create one
        </Link>
      </p>
    </AuthShell>
  );
}
