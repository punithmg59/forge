import Link from "next/link";

export function FinalCTA() {
  return (
    <section className="py-24 md:py-32 px-6">
      <div className="max-w-4xl mx-auto text-center">
        {/* Headline */}
        <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-6">
          Stop managing your startup from disconnected tools.
        </h2>

        {/* Supporting */}
        <p className="text-lg text-white/50 max-w-2xl mx-auto mb-12">
          Build a company that can reason, execute, and learn.
        </p>

        {/* CTAs */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
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
            Explore the operating model
          </a>
        </div>
      </div>
    </section>
  );
}
