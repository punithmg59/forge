import type { ReactNode } from "react";

export function AuthShell({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
}) {
  return (
    <div className="grid-bg relative min-h-screen overflow-hidden">
      <div
        className="orb orb-purple"
        style={{ width: 600, height: 600, top: "-150px", left: "-150px" }}
      />
      <div
        className="orb orb-blue"
        style={{ width: 500, height: 500, bottom: "-100px", right: "-100px" }}
      />
      <main className="relative z-10 flex min-h-screen items-center justify-center px-6 py-12">
        <div className="glass-card w-full max-w-md p-8">
          <p className="mb-2 text-xs font-semibold tracking-widest uppercase text-white/40">
            Forge
          </p>
          <h1 className="mb-2 text-2xl font-semibold">{title}</h1>
          <p className="mb-8 text-sm text-white/50">{subtitle}</p>
          {children}
        </div>
      </main>
    </div>
  );
}
