export function FounderControl() {
  return (
    <section className="py-24 md:py-32 px-6 bg-white/[0.01]">
      <div className="max-w-6xl mx-auto">
        {/* Section header */}
        <div className="text-center mb-16">
          <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-6">
            AI with initiative. Humans with authority.
          </h2>
          <p className="text-lg text-white/50 max-w-2xl mx-auto">
            Forge is built around a simple principle: intelligence can be autonomous, but consequential action remains under founder control.
          </p>
        </div>

        {/* Three principles */}
        <div className="grid md:grid-cols-3 gap-8">
          <ControlCard
            title="PROPOSE"
            description="AI can analyze context and propose actions."
            icon="💡"
          />
          <ControlCard
            title="VERIFY"
            description="Plans are validated against server-side rules, permissions, tools, and company boundaries."
            icon="🔒"
          />
          <ControlCard
            title="APPROVE"
            description="The founder explicitly authorizes consequential execution."
            icon="✓"
          />
        </div>
      </div>
    </section>
  );
}

function ControlCard({ title, description, icon }: { title: string; description: string; icon: string }) {
  return (
    <div className="glass-card p-8 border-violet-500/10 hover:border-violet-500/20 transition-colors">
      <div className="text-3xl mb-4">{icon}</div>
      <h3 className="text-xl font-semibold text-white mb-3">{title}</h3>
      <p className="text-sm text-white/60 leading-relaxed">{description}</p>
    </div>
  );
}
