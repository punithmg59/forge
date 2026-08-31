import Link from "next/link";

import type { ObjectiveTaskLearning } from "@/lib/api";
import { EXECUTION_CONTEXT_MESSAGES } from "@/lib/execution-context";
import { formatLearningStatus, learningStatusHint } from "@/lib/tasks";

export function TaskLearningSection({ learnings }: { learnings: ObjectiveTaskLearning[] }) {
  return (
    <section className="glass-card p-6" aria-labelledby="learning-heading">
      <p className="forge-label">Learning</p>
      <h2 id="learning-heading" className="text-base font-medium text-white">Learning</h2>
      {learnings.length === 0 ? (
        <p className="mt-3 text-sm text-white/50">{EXECUTION_CONTEXT_MESSAGES.learningEmpty}</p>
      ) : (
        <div className="mt-3 space-y-4">
          {learnings.map((learning) => (
            <article
              key={learning.id}
              className="rounded-xl border border-white/8 bg-white/3 p-4"
            >
              <p className="text-sm text-white/85 whitespace-pre-wrap">{learning.statement}</p>
              {learning.evidence_summary ? (
                <p className="mt-2 text-xs text-white/50">
                  Evidence summary: {learning.evidence_summary}
                </p>
              ) : null}
              <p className="mt-2 text-xs font-semibold tracking-wide text-white/55">
                Status: {formatLearningStatus(learning.status)}
              </p>
              {learningStatusHint(learning.status) ? (
                <p className="mt-1 text-xs text-white/45">{learningStatusHint(learning.status)}</p>
              ) : null}
              {learning.status === "active" ? (
                <Link
                  href="/dashboard#company-brain"
                  className="mt-3 inline-block text-sm text-violet-200/80 transition hover:text-violet-100"
                >
                  View in Company Brain →
                </Link>
              ) : null}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
