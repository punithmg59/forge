import Link from "next/link";

export function Hero() {
  return (
    <section className="relative min-h-screen flex flex-col items-center justify-center px-6 py-24 md:py-32">
      {/* Eyebrow */}
      <div className="animate-fade-in-up mb-6">
        <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-violet-500/30 bg-violet-500/10 text-xs font-medium tracking-wider uppercase text-violet-200">
          <span className="w-1.5 h-1.5 rounded-full bg-violet-400" />
          The AI Operating System for Founders
        </span>
      </div>

      {/* Main headline */}
      <h1 className="forge-logo-text animate-fade-in-up animate-delay-1 text-4xl md:text-6xl lg:text-7xl font-black tracking-tight text-center max-w-5xl mb-6 leading-tight">
        Run your company with an AI operating system.
      </h1>

      {/* Supporting line */}
      <p className="animate-fade-in-up animate-delay-2 text-lg md:text-xl text-white/60 font-light max-w-3xl text-center mb-8 leading-relaxed">
        Forge turns your company's context into grounded recommendations, controlled execution, and institutional memory.
      </p>

      {/* Supporting paragraph */}
      <p className="animate-fade-in-up animate-delay-2 text-base md:text-lg text-white/40 max-w-2xl text-center mb-12 leading-relaxed">
        Bring your objectives, decisions, evidence, tasks, and company knowledge into one operating system. Forge helps you decide what matters, execute with control, and learn from what happens.
      </p>

      {/* CTAs */}
      <div className="animate-fade-in-up animate-delay-3 flex flex-col sm:flex-row items-center gap-4 mb-16">
        <Link
          className="w-full sm:w-auto px-8 py-4 rounded-xl bg-gradient-to-b from-violet-500 to-violet-600 text-white font-semibold text-base hover:from-violet-400 hover:to-violet-500 transition-all shadow-lg shadow-violet-500/25"
          href="/signup"
        >
          Start building with Forge
        </Link>
        <a
          className="w-full sm:w-auto px-8 py-4 rounded-xl border border-white/12 bg-white/5 text-white font-medium text-base hover:bg-white/10 transition-colors"
          href="#how-it-works"
        >
          See how Forge works
        </a>
      </div>

      {/* Hero Visual - Operating Flow */}
      <div className="animate-fade-in-up animate-delay-3 w-full max-w-4xl">
        <div className="glass-card p-8 md:p-12">
          <div className="flex flex-col items-center gap-4">
            {/* FORGE header */}
            <div className="text-center mb-4">
              <span className="text-xs font-semibold tracking-widest uppercase text-white/40">
                FORGE OPERATING FLOW
              </span>
            </div>

            {/* Flow diagram */}
            <div className="flex flex-col md:flex-row items-center justify-center gap-3 md:gap-4 w-full">
              <FlowNode label="Company Context" icon="🧠" />
              <Arrow />
              <FlowNode label="Forge Intelligence" icon="⚡" />
              <Arrow />
              <FlowNode label="Recommendation" icon="💡" />
            </div>

            <div className="flex flex-col md:flex-row items-center justify-center gap-3 md:gap-4 w-full mt-2">
              <FlowNode label="Founder Approval" icon="✓" />
              <Arrow />
              <FlowNode label="Execution" icon="⚙️" />
              <Arrow />
              <FlowNode label="Evidence" icon="📊" />
            </div>

            <div className="flex flex-col md:flex-row items-center justify-center gap-3 md:gap-4 w-full mt-2">
              <FlowNode label="Company Learning" icon="🧠" />
              <Arrow />
              <div className="flex-1 flex items-center justify-center">
                <div className="text-xs text-white/30 font-mono">
                  ← Loop closes →
                </div>
              </div>
              <Arrow />
              <FlowNode label="Better Decisions" icon="🎯" />
            </div>
          </div>
        </div>
      </div>

      {/* Brand message */}
      <div className="animate-fade-in-up animate-delay-3 mt-12 text-center">
        <p className="text-sm text-white/30 font-medium">
          AI proposes. Founders decide. Forge remembers.
        </p>
      </div>
    </section>
  );
}

function FlowNode({ label, icon }: { label: string; icon: string }) {
  return (
    <div className="flex-1 min-w-[140px] max-w-[180px]">
      <div className="border border-white/10 bg-white/[0.02] rounded-lg p-4 text-center">
        <div className="text-2xl mb-2">{icon}</div>
        <div className="text-xs font-medium text-white/70">{label}</div>
      </div>
    </div>
  );
}

function Arrow() {
  return (
    <div className="hidden md:flex items-center justify-center text-white/20">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M5 12h14M12 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </div>
  );
}
