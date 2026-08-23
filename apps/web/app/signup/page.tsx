"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { AuthShell } from "@/components/AuthShell";
import { ApiError, register } from "@/lib/api";

export default function SignupPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (!name.trim() || !email.trim() || !password || !confirmPassword) {
      setError("All fields are required.");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    setPending(true);
    try {
      await register({ name: name.trim(), email: email.trim(), password });
      router.replace("/onboarding");
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setError("An account with this email already exists.");
      } else if (err instanceof ApiError && err.status === 422) {
        setError("Please check your name, email, and password.");
      } else {
        setError("Unable to create your account. Please try again.");
      }
    } finally {
      setPending(false);
    }
  }

  return (
    <AuthShell title="Create your account" subtitle="Start with a secure session, then set up your company.">
      <form onSubmit={onSubmit} className="space-y-4">
        <div>
          <label className="forge-label" htmlFor="name">
            Name
          </label>
          <input
            id="name"
            className="forge-input"
            value={name}
            onChange={(event) => setName(event.target.value)}
            autoComplete="name"
          />
        </div>
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
            autoComplete="new-password"
          />
        </div>
        <div>
          <label className="forge-label" htmlFor="confirmPassword">
            Confirm password
          </label>
          <input
            id="confirmPassword"
            className="forge-input"
            type="password"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            autoComplete="new-password"
          />
        </div>
        {error ? <p className="text-sm text-red-400">{error}</p> : null}
        <button className="forge-button" type="submit" disabled={pending}>
          {pending ? "Creating account..." : "Create account"}
        </button>
      </form>
      <p className="mt-6 text-center text-sm text-white/40">
        Already registered?{" "}
        <Link className="text-violet-300" href="/login">
          Login
        </Link>
      </p>
    </AuthShell>
  );
}
