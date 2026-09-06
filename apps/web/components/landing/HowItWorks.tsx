import Link from "next/link";

export function HowItWorks() {
  return (
    <section className="py-24 md:py-32 px-6">
      <div className="max-w-6xl mx-auto">
        {/* Section header */}
        <div className="text-center mb-16">
          <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-6">
            Start with your company. Not a blank chat.
          </h2>
        </div>

        {/* Three steps */}
        <div className="grid md:grid-cols-3 gap-8 mb-16">
          <StepCard
            number="01"
            title="DEFINE"
            description="Set your company objective and operating context."
          />
          <StepCard
            number="02"
            title="CONNECT"
            description="Build your Company Brain from decisions, evidence, and organizational knowledge."
          />
          <StepCard
            number="03"
            title="OPERATE"
            description="Ask Forge what to do next, review recommendations, approve actions, execute, and learn."
          />
        </div>

        {/* CTA */}
        <div className="text-center">
          <Link
            className="inline-block px-8 py-4 rounded-xl bg-gradient-to-b from-violet-500 to-violet-600 text-white font-semibold text-base hover:from-violet-400 hover:to-violet-500 transition-all shadow-lg shadow-violet-500/25"
            href="/signup"
          >
            Enter Forge
          </Link>
        </div>
      </div>
    </section>
  );
}

function StepCard({ number, title, description }: { number: string; title: string; description: string }) {
  return (
    <div className="glass-card p-8 text-center">
      <div className="text-4xl font-bold text-violet-400 mb-4">{number}</div>
      <h3 className="text-xl font-semibold text-white mb-3">{title}</h3>
      <p className="text-sm text-white/60 leading-relaxed">{description}</p>
    </div>
  );
}
