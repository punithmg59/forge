"use client";

import { useState } from "react";

import type { ObjectiveTaskEvidence } from "@/lib/api";
import { EXECUTION_CONTEXT_MESSAGES } from "@/lib/execution-context";
import { formatTaskTimestamp, parseEvidenceContent } from "@/lib/tasks";

export function TaskEvidenceSection({ evidence }: { evidence: ObjectiveTaskEvidence[] }) {
  return (
    <section className="glass-card p-6" aria-labelledby="evidence-heading">
      <p className="forge-label">Evidence</p>
      <h2 id="evidence-heading" className="text-base font-medium text-white">Evidence</h2>
      {evidence.length === 0 ? (
        <p className="mt-3 text-sm text-white/50">{EXECUTION_CONTEXT_MESSAGES.evidenceEmpty}</p>
      ) : (
        <div className="mt-3 space-y-4">
          {evidence.map((item) => (
            <EvidenceCard key={item.id} item={item} />
          ))}
        </div>
      )}
    </section>
  );
}

function EvidenceCard({ item }: { item: ObjectiveTaskEvidence }) {
  const [showRaw, setShowRaw] = useState(false);
  const parsed = parseEvidenceContent(item.content);

  return (
    <article className="rounded-xl border border-white/8 bg-white/3 p-4">
      <h3 className="font-medium text-white">{item.title}</h3>
      <p className="mt-1 text-xs text-white/45">
        Type: {item.type} · Source: {item.source_type}
        {item.observed_at ? ` · Observed ${formatTaskTimestamp(item.observed_at)}` : ""}
      </p>
      {item.source_reference ? (
        <p className="mt-2 text-xs text-white/45">Reference: {item.source_reference}</p>
      ) : null}

      {parsed?.result_summary ? (
        <div className="mt-3 space-y-3 text-sm">
          <div>
            <p className="text-white/45">Summary</p>
            <p className="mt-1 text-white/80 whitespace-pre-wrap">
              {String(parsed.result_summary)}
            </p>
          </div>
          {parsed.result_metrics && typeof parsed.result_metrics === "object" ? (
            <MetricsPreview metrics={parsed.result_metrics as Record<string, unknown>} />
          ) : null}
          {parsed.result_notes ? (
            <div>
              <p className="text-white/45">Notes</p>
              <p className="mt-1 text-white/80 whitespace-pre-wrap">
                {String(parsed.result_notes)}
              </p>
            </div>
          ) : null}
        </div>
      ) : (
        <p className="mt-3 text-sm text-white/75 whitespace-pre-wrap">{item.content}</p>
      )}

      <button
        type="button"
        className="mt-3 text-xs text-violet-200/80 transition hover:text-violet-100"
        onClick={() => setShowRaw((current) => !current)}
        aria-expanded={showRaw}
      >
        {showRaw ? "Hide raw details" : "View raw details"}
      </button>
      {showRaw ? (
        <pre className="mt-2 overflow-x-auto rounded-lg border border-white/8 bg-black/20 p-3 text-xs text-white/70">
          {item.content}
        </pre>
      ) : null}
    </article>
  );
}

function MetricsPreview({ metrics }: { metrics: Record<string, unknown> }) {
  const entries = Object.entries(metrics);
  if (entries.length === 0) {
    return null;
  }
  return (
    <div>
      <p className="text-white/45">Metrics</p>
      <table className="mt-2 w-full text-left text-sm">
        <tbody>
          {entries.map(([key, value]) => (
            <tr key={key} className="border-t border-white/6 first:border-t-0">
              <td className="py-2 pr-4 text-white/70">{key}</td>
              <td className="py-2 text-white/80">{String(value)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
