export function WhatForgeDoes() {
  return (
    <section className="py-24 md:py-32 px-6 bg-white/[0.01]">
      <div className="max-w-6xl mx-auto">
        {/* Section header */}
        <div className="text-center mb-16">
          <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-6">
            One operating system. Four intelligence layers.
          </h2>
        </div>

        {/* Cards */}
        <div className="grid md:grid-cols-2 gap-8">
          <FeatureCard
            title="Company Brain"
            subtitle="Your company's evolving memory."
            description="Forge connects objectives, facts, beliefs, decisions, evidence, and learnings into a structured company context."
            icon="🧠"
          />
          <FeatureCard
            title="Forge Intelligence"
            subtitle="Turn company context into grounded recommendations."
            description="The Head Agent reasons over company context and can coordinate specialized intelligence."
            icon="⚡"
          />
          <FeatureCard
            title="Specialized Agents"
            subtitle="Bring domain expertise into the operating loop."
            description={
              <>
                <p className="mb-2">Customer & Growth helps with acquisition, retention, customer discovery, pricing, and growth.</p>
                <p>Product helps with roadmap, features, prioritization, product quality, UX, and product strategy.</p>
              </>
            }
            icon="🎯"
          />
          <FeatureCard
            title="Controlled Execution"
            subtitle="Move from recommendation to action without giving up control."
            description={
              <>
                <p className="mb-2">Forge can construct validated execution plans and execute only after explicit founder authorization.</p>
                <p className="text-violet-300 font-medium">AI proposes. You approve. Forge executes within defined boundaries.</p>
              </>
            }
            icon="⚙️"
          />
        </div>
      </div>
    </section>
  );
}

function FeatureCard({
  title,
  subtitle,
  description,
  icon,
}: {
  title: string;
  subtitle: string;
  description: React.ReactNode;
  icon: string;
}) {
  return (
    <div className="glass-card p-8">
      <div className="text-4xl mb-4">{icon}</div>
      <h3 className="text-xl font-semibold text-white mb-2">{title}</h3>
      <p className="text-sm text-violet-300 mb-4">{subtitle}</p>
      <div className="text-sm text-white/60 leading-relaxed">{description}</div>
    </div>
  );
}
