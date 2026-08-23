"use client";

import { useEffect, useState } from "react";

export default function HomePage() {
  const [backendStatus, setBackendStatus] = useState<"checking" | "online" | "offline">("checking");

  // Simulate backend connectivity check
  useEffect(() => {
    const check = async () => {
      try {
        const res = await fetch("http://localhost:8000/api/v1/health", {
          signal: AbortSignal.timeout(3000),
        });
        setBackendStatus(res.ok ? "online" : "offline");
      } catch {
        setBackendStatus("offline");
      }
    };
    check();
  }, []);

  return (
    <div className="grid-bg relative min-h-screen overflow-hidden">
      {/* Background orbs */}
      <div
        className="orb orb-purple"
        style={{ width: 600, height: 600, top: "-150px", left: "-150px" }}
      />
      <div
        className="orb orb-blue"
        style={{ width: 500, height: 500, bottom: "-100px", right: "-100px" }}
      />

      {/* Top nav */}
      <nav className="nav-bar relative z-10 flex items-center justify-between px-6 py-3">
        <div className="flex items-center gap-2">
          {/* Flame icon */}
          <svg
            width="22"
            height="22"
            viewBox="0 0 24 24"
            fill="none"
            className="text-amber-400"
          >
            <path
              d="M12 2C12 2 7 8 7 13a5 5 0 0 0 10 0c0-2-1-4-2-5.5C14 9 13 10 12 11c0-3 0-6 0-9Z"
              fill="currentColor"
              opacity="0.9"
            />
            <path
              d="M12 14c0 1.1-.9 2-2 2s-2-.9-2-2c0-1.5 2-4 2-4s2 2.5 2 4Z"
              fill="#fbbf24"
            />
          </svg>
          <span className="text-sm font-semibold tracking-widest uppercase text-white/80">
            FORGE
          </span>
        </div>

        <div className="flex items-center gap-3">
          <a className="text-sm text-white/60 hover:text-white" href="/login">
            Login
          </a>
          <a className="text-sm text-violet-300 hover:text-white" href="/signup">
            Signup
          </a>
          <span className="status-badge status-badge-online">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400" />
            v0.1.0-alpha
          </span>
        </div>
      </nav>

      {/* Main content */}
      <main className="relative z-10 flex flex-col items-center justify-center min-h-[calc(100vh-56px)] px-6 text-center">
        {/* Hero */}
        <div className="animate-fade-in-up animate-delay-1 mb-3">
          <span className="status-badge status-badge-online text-xs mb-6 inline-flex">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400" />
            System Initialized
          </span>
        </div>

        <h1 className="forge-logo-text animate-fade-in-up animate-delay-1 text-7xl md:text-8xl font-black tracking-tight mb-4">
          Forge
        </h1>

        <p className="animate-fade-in-up animate-delay-2 text-lg md:text-xl text-white/50 font-light max-w-md leading-relaxed mb-12">
          The Operating System for{" "}
          <span className="text-white/80 font-medium">Ambitious Solo Founders</span>
        </p>

        {/* System Status Card */}
        <div className="animate-fade-in-up animate-delay-3 glass-card w-full max-w-sm p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-xs font-semibold tracking-widest uppercase text-white/40">
              System Status
            </h2>
            <span className="text-xs text-white/20 font-mono">
              {new Date().toISOString().slice(0, 10)}
            </span>
          </div>

          <div className="space-y-3">
            {/* Frontend row */}
            <div className="flex items-center justify-between py-3 border-b border-white/5">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                    <rect x="3" y="3" width="18" height="18" rx="3" stroke="#10b981" strokeWidth="2"/>
                    <path d="M9 12l2 2 4-4" stroke="#10b981" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </div>
                <span className="text-sm text-white/70">Frontend</span>
              </div>
              <span className="status-badge status-badge-online">
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400" />
                Online
              </span>
            </div>

            {/* Backend row */}
            <div className="flex items-center justify-between py-3">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-amber-500/10 flex items-center justify-center">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                    <circle cx="12" cy="12" r="9" stroke="#f59e0b" strokeWidth="2"/>
                    <path d="M12 7v5l3 3" stroke="#f59e0b" strokeWidth="2" strokeLinecap="round"/>
                  </svg>
                </div>
                <span className="text-sm text-white/70">Backend</span>
              </div>
              {backendStatus === "checking" && (
                <span className="status-badge status-badge-checking">
                  <span className="pulse-dot inline-block w-1.5 h-1.5 rounded-full bg-amber-400" />
                  Checking...
                </span>
              )}
              {backendStatus === "online" && (
                <span className="status-badge status-badge-online">
                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  Online
                </span>
              )}
              {backendStatus === "offline" && (
                <span className="status-badge" style={{ color: "#f87171", borderColor: "rgba(248,113,113,0.3)", background: "rgba(248,113,113,0.08)" }}>
                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-red-400" />
                  Offline
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Footer hint */}
        <p className="animate-fade-in-up animate-delay-3 mt-8 text-xs text-white/20 font-mono tracking-wider">
          AUTH READY · COMPANY OS FOUNDATION
        </p>
      </main>
    </div>
  );
}
