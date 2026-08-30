"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { TaskDialog } from "@/components/tasks/TaskDialog";
import { TaskEvidenceSection } from "@/components/tasks/TaskEvidenceSection";
import { TaskExecutionResultSection } from "@/components/tasks/TaskExecutionResultSection";
import { TaskLearningSection } from "@/components/tasks/TaskLearningSection";
import { TaskProvenance } from "@/components/tasks/TaskProvenance";
import { TaskStatusBadge } from "@/components/tasks/TaskStatusBadge";
import { TaskWhySection } from "@/components/tasks/TaskWhySection";
import {
  ApiError,
  type ObjectiveTaskDetail,
  type ObjectiveTaskPriority,
  completeObjectiveTask,
  getObjectiveTaskDetail,
  transitionObjectiveTaskStatus,
  updateObjectiveTask,
} from "@/lib/api";
import {
  buildProvenanceChain,
  describeWorkflowNextStep,
} from "@/lib/execution-context";
import {
  canBlockTask,
  canCompleteTask,
  canResumeTask,
  canStartTask,
  formatTaskTimestamp,
  isTerminalTaskStatus,
  mapTaskApiError,
  TASK_PRIORITIES,
  taskStatusLabel,
  validateBlockedReason,
  validateCompletionForm,
  type CompletionFormValues,
} from "@/lib/tasks";

type TaskDetailViewProps = {
  companyId: string;
  taskId: string;
};

type MetricRow = { key: string; value: string };

export function TaskDetailView({ companyId, taskId }: TaskDetailViewProps) {
  const [task, setTask] = useState<ObjectiveTaskDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const [blockOpen, setBlockOpen] = useState(false);
  const [completeOpen, setCompleteOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);

  const loadTask = useCallback(async () => {
    const requestedCompanyId = companyId;
    const requestedTaskId = taskId;
    setLoading(true);
    setError(null);
    setNotFound(false);
    setTask(null);
    try {
      const detail = await getObjectiveTaskDetail(requestedCompanyId, requestedTaskId);
      if (requestedCompanyId !== companyId || requestedTaskId !== taskId) {
        return;
      }
      setTask(detail);
    } catch (err) {
      if (requestedCompanyId !== companyId || requestedTaskId !== taskId) {
        return;
      }
      if (err instanceof ApiError && err.status === 404) {
        setNotFound(true);
        setTask(null);
      } else {
        setError(mapTaskApiError(err, "Unable to load this task. Please try again."));
      }
    } finally {
      if (requestedCompanyId === companyId && requestedTaskId === taskId) {
        setLoading(false);
      }
    }
  }, [companyId, taskId]);

  useEffect(() => {
    void loadTask();
  }, [loadTask]);

  async function runAction(
    key: string,
    action: () => Promise<void>,
  ) {
    if (actionLoading) {
      return;
    }
    setActionLoading(key);
    setActionError(null);
    try {
      await action();
      await loadTask();
    } catch (err) {
      setActionError(mapTaskApiError(err, "This action could not be completed. Please try again."));
    } finally {
      setActionLoading(null);
    }
  }

  async function onStart() {
    await runAction("start", async () => {
      await transitionObjectiveTaskStatus(companyId, taskId, { status: "in_progress" });
    });
  }

  async function onResume() {
    await runAction("resume", async () => {
      await transitionObjectiveTaskStatus(companyId, taskId, { status: "in_progress" });
    });
  }

  if (loading) {
    return <TaskDetailSkeleton />;
  }

  if (notFound) {
    return <TaskNotFound />;
  }

  if (error || !task) {
    return (
      <div className="glass-card p-6 text-sm text-red-200/90">
        <p>{error ?? "Unable to load this task."}</p>
        <button className="forge-button-secondary mt-4" type="button" onClick={() => void loadTask()}>
          Try again
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Link
        href="/dashboard/tasks"
        className="text-sm text-white/55 transition hover:text-white/80"
      >
        ← Back to Founder Tasks
      </Link>

      <header className="glass-card p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="space-y-2 min-w-0">
            <h1 className="text-2xl font-semibold text-white">{task.title}</h1>
            {task.objective ? (
              <p className="text-sm text-white/60">
                Objective: <span className="text-white/80">{task.objective.title}</span>
              </p>
            ) : (
              <p className="text-sm text-white/45">Objective information unavailable.</p>
            )}
          </div>
          <TaskStatusBadge status={task.status} />
        </div>
        <div className="mt-4 flex flex-wrap gap-x-6 gap-y-2 text-sm text-white/55">
          <span>Priority: {task.priority}</span>
          <span>Status: {taskStatusLabel(task.status)}</span>
          {task.started_at ? <span>Started: {formatTaskTimestamp(task.started_at)}</span> : null}
        </div>
        {task.description ? (
          <p className="mt-4 text-sm leading-relaxed text-white/70 whitespace-pre-wrap">
            {task.description}
          </p>
        ) : null}
      </header>

      {actionError ? (
        <div className="rounded-xl border border-red-400/25 bg-red-500/10 px-4 py-3 text-sm text-red-200/90">
          {actionError}
        </div>
      ) : null}

      <TaskWhySection task={task} />

      <section className="glass-card p-6" aria-labelledby="execution-heading">
        <p className="forge-label">Execution</p>
        <h2 id="execution-heading" className="text-base font-medium text-white">Execution</h2>
        <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-2">
          <DetailItem label="Status" value={taskStatusLabel(task.status)} />
          <DetailItem label="Started" value={formatTaskTimestamp(task.started_at)} />
          <DetailItem label="Updated" value={formatTaskTimestamp(task.updated_at)} />
          {task.blocked_reason ? (
            <DetailItem label="Blocked reason" value={task.blocked_reason} />
          ) : null}
        </dl>
        <p className="mt-4 text-sm text-white/55">{describeWorkflowNextStep(task)}</p>
        <ExecutionPanel
          task={task}
          actionLoading={actionLoading}
          onStart={() => void onStart()}
          onResume={() => void onResume()}
          onBlock={() => setBlockOpen(true)}
          onComplete={() => setCompleteOpen(true)}
        />
        {!isTerminalTaskStatus(task.status) ? (
          <button
            className="forge-button-secondary mt-4"
            type="button"
            onClick={() => setEditOpen(true)}
          >
            Edit task details
          </button>
        ) : null}
      </section>

      <TaskExecutionResultSection task={task} />
      <TaskEvidenceSection evidence={task.evidence} />
      <TaskLearningSection learnings={task.learnings} />
      <TaskProvenance nodes={buildProvenanceChain(task)} />

      <BlockTaskDialog
        open={blockOpen}
        loading={actionLoading === "block"}
        onClose={() => setBlockOpen(false)}
        onSubmit={async (reason) => {
          await runAction("block", async () => {
            await transitionObjectiveTaskStatus(companyId, taskId, {
              status: "blocked",
              blocked_reason: reason,
            });
            setBlockOpen(false);
          });
        }}
      />

      <CompleteTaskDialog
        open={completeOpen}
        loading={actionLoading === "complete"}
        onClose={() => setCompleteOpen(false)}
        onSubmit={async (values) => {
          await runAction("complete", async () => {
            const metrics =
              Object.keys(values.result_metrics).length > 0
                ? values.result_metrics
                : undefined;
            const notes = values.result_notes.trim() || undefined;
            await completeObjectiveTask(companyId, taskId, {
              result_summary: values.result_summary.trim(),
              result_metrics: metrics,
              result_notes: notes,
            });
            setCompleteOpen(false);
          });
        }}
      />

      <EditTaskDialog
        open={editOpen}
        task={task}
        loading={actionLoading === "edit"}
        onClose={() => setEditOpen(false)}
        onSubmit={async (payload) => {
          await runAction("edit", async () => {
            await updateObjectiveTask(companyId, taskId, payload);
            setEditOpen(false);
          });
        }}
      />
    </div>
  );
}

function DetailItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-white/45">{label}</dt>
      <dd className="text-white/75">{value}</dd>
    </div>
  );
}

function ExecutionPanel({
  task,
  actionLoading,
  onStart,
  onResume,
  onBlock,
  onComplete,
}: {
  task: ObjectiveTaskDetail;
  actionLoading: string | null;
  onStart: () => void;
  onResume: () => void;
  onBlock: () => void;
  onComplete: () => void;
}) {
  if (isTerminalTaskStatus(task.status)) {
    return (
      <p className="mt-2 text-sm text-white/60">
        This task is completed. No further execution actions are available.
      </p>
    );
  }

  return (
    <div className="mt-3 flex flex-wrap gap-3">
      {canStartTask(task.status) ? (
        <button
          className="forge-button w-auto px-5"
          type="button"
          disabled={actionLoading !== null}
          onClick={onStart}
        >
          {actionLoading === "start" ? "Starting..." : "Start task"}
        </button>
      ) : null}
      {canResumeTask(task.status) ? (
        <button
          className="forge-button w-auto px-5"
          type="button"
          disabled={actionLoading !== null}
          onClick={onResume}
        >
          {actionLoading === "resume" ? "Resuming..." : "Resume task"}
        </button>
      ) : null}
      {canBlockTask(task.status) ? (
        <button
          className="forge-button-danger"
          type="button"
          disabled={actionLoading !== null}
          onClick={onBlock}
        >
          Mark blocked
        </button>
      ) : null}
      {canCompleteTask(task.status) ? (
        <button
          className="forge-button-secondary"
          type="button"
          disabled={actionLoading !== null}
          onClick={onComplete}
        >
          Complete task
        </button>
      ) : null}
    </div>
  );
}

function BlockTaskDialog({
  open,
  loading,
  onClose,
  onSubmit,
}: {
  open: boolean;
  loading: boolean;
  onClose: () => void;
  onSubmit: (reason: string) => Promise<void>;
}) {
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setReason("");
      setError(null);
    }
  }, [open]);

  return (
    <TaskDialog open={open} title="Mark task as blocked" onClose={onClose}>
      <label className="forge-label" htmlFor="blocked-reason">Blocked reason *</label>
      <textarea
        id="blocked-reason"
        className="forge-input mt-1 min-h-[100px]"
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        placeholder="Waiting for customer interview access."
      />
      {error ? <p className="mt-2 text-sm text-red-300/90">{error}</p> : null}
      <div className="mt-4 flex gap-3">
        <button className="forge-button-secondary" type="button" onClick={onClose} disabled={loading}>
          Cancel
        </button>
        <button
          className="forge-button w-auto px-5"
          type="button"
          disabled={loading}
          onClick={() => {
            const validation = validateBlockedReason(reason);
            if (validation) {
              setError(validation);
              return;
            }
            void onSubmit(reason.trim());
          }}
        >
          {loading ? "Saving..." : "Mark blocked"}
        </button>
      </div>
    </TaskDialog>
  );
}

function CompleteTaskDialog({
  open,
  loading,
  onClose,
  onSubmit,
}: {
  open: boolean;
  loading: boolean;
  onClose: () => void;
  onSubmit: (values: CompletionFormValues) => Promise<void>;
}) {
  const [summary, setSummary] = useState("");
  const [notes, setNotes] = useState("");
  const [metrics, setMetrics] = useState<MetricRow[]>([]);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [confirmed, setConfirmed] = useState(false);

  useEffect(() => {
    if (open) {
      setSummary("");
      setNotes("");
      setMetrics([]);
      setErrors({});
      setConfirmed(false);
    }
  }, [open]);

  function buildValues(): CompletionFormValues {
    const result_metrics: Record<string, number> = {};
    for (const row of metrics) {
      const key = row.key.trim();
      const num = Number(row.value);
      if (key && Number.isFinite(num)) {
        result_metrics[key] = num;
      }
    }
    return {
      result_summary: summary,
      result_metrics,
      result_notes: notes,
    };
  }

  return (
    <TaskDialog open={open} title="Complete task" onClose={onClose}>
      <p className="text-sm text-white/55">
        Completing this task is final. The result will be recorded as Evidence.
      </p>
      <div className="mt-4 space-y-4">
        <div>
          <label className="forge-label" htmlFor="result-summary">Result summary *</label>
          <textarea
            id="result-summary"
            className="forge-input mt-1 min-h-[100px]"
            value={summary}
            onChange={(e) => setSummary(e.target.value)}
          />
          {errors.result_summary ? (
            <p className="mt-1 text-sm text-red-300/90">{errors.result_summary}</p>
          ) : null}
        </div>
        <div>
          <p className="forge-label">Result metrics</p>
          <div className="mt-2 space-y-2">
            {metrics.map((row, index) => (
              <div key={index} className="flex gap-2">
                <input
                  className="forge-input"
                  placeholder="Metric name"
                  value={row.key}
                  onChange={(e) => {
                    const next = [...metrics];
                    next[index] = { ...next[index], key: e.target.value };
                    setMetrics(next);
                  }}
                />
                <input
                  className="forge-input"
                  placeholder="Value"
                  type="number"
                  value={row.value}
                  onChange={(e) => {
                    const next = [...metrics];
                    next[index] = { ...next[index], value: e.target.value };
                    setMetrics(next);
                  }}
                />
                <button
                  type="button"
                  className="forge-button-secondary shrink-0 px-3"
                  onClick={() => setMetrics(metrics.filter((_, i) => i !== index))}
                >
                  Remove
                </button>
              </div>
            ))}
            <button
              type="button"
              className="forge-button-secondary"
              onClick={() => setMetrics([...metrics, { key: "", value: "" }])}
            >
              Add metric
            </button>
          </div>
          {errors.metrics ? (
            <p className="mt-1 text-sm text-red-300/90">{errors.metrics}</p>
          ) : null}
        </div>
        <div>
          <label className="forge-label" htmlFor="result-notes">Result notes</label>
          <textarea
            id="result-notes"
            className="forge-input mt-1 min-h-[80px]"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
          {errors.result_notes ? (
            <p className="mt-1 text-sm text-red-300/90">{errors.result_notes}</p>
          ) : null}
        </div>
        <label className="flex items-start gap-2 text-sm text-white/65">
          <input
            type="checkbox"
            checked={confirmed}
            onChange={(e) => setConfirmed(e.target.checked)}
            className="mt-1"
          />
          I understand completion is final and will create Evidence.
        </label>
      </div>
      <div className="mt-4 flex gap-3">
        <button className="forge-button-secondary" type="button" onClick={onClose} disabled={loading}>
          Cancel
        </button>
        <button
          className="forge-button w-auto px-5"
          type="button"
          disabled={loading || !confirmed}
          onClick={() => {
            const values = buildValues();
            const validation = validateCompletionForm(values);
            if (Object.keys(validation).length > 0) {
              setErrors(validation as Record<string, string>);
              return;
            }
            setErrors({});
            void onSubmit(values);
          }}
        >
          {loading ? "Completing..." : "Complete task"}
        </button>
      </div>
    </TaskDialog>
  );
}

function EditTaskDialog({
  open,
  task,
  loading,
  onClose,
  onSubmit,
}: {
  open: boolean;
  task: ObjectiveTaskDetail;
  loading: boolean;
  onClose: () => void;
  onSubmit: (payload: {
    title: string;
    description: string | null;
    priority: ObjectiveTaskPriority;
  }) => Promise<void>;
}) {
  const [title, setTitle] = useState(task.title);
  const [description, setDescription] = useState(task.description ?? "");
  const [priority, setPriority] = useState<ObjectiveTaskPriority>(
    (task.priority as ObjectiveTaskPriority) ?? "medium",
  );
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setTitle(task.title);
      setDescription(task.description ?? "");
      setPriority((task.priority as ObjectiveTaskPriority) ?? "medium");
      setError(null);
    }
  }, [open, task]);

  return (
    <TaskDialog open={open} title="Edit task" onClose={onClose}>
      <div className="space-y-4">
        <div>
          <label className="forge-label" htmlFor="edit-title">Title</label>
          <input
            id="edit-title"
            className="forge-input mt-1"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </div>
        <div>
          <label className="forge-label" htmlFor="edit-description">Description</label>
          <textarea
            id="edit-description"
            className="forge-input mt-1 min-h-[100px]"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
        <div>
          <label className="forge-label" htmlFor="edit-priority">Priority</label>
          <select
            id="edit-priority"
            className="forge-input mt-1"
            value={priority}
            onChange={(e) => setPriority(e.target.value as ObjectiveTaskPriority)}
          >
            {TASK_PRIORITIES.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
        </div>
        {error ? <p className="text-sm text-red-300/90">{error}</p> : null}
      </div>
      <div className="mt-4 flex gap-3">
        <button className="forge-button-secondary" type="button" onClick={onClose} disabled={loading}>
          Cancel
        </button>
        <button
          className="forge-button w-auto px-5"
          type="button"
          disabled={loading}
          onClick={() => {
            const trimmedTitle = title.trim();
            if (!trimmedTitle) {
              setError("Title cannot be blank.");
              return;
            }
            setError(null);
            void onSubmit({
              title: trimmedTitle,
              description: description.trim() || null,
              priority,
            });
          }}
        >
          {loading ? "Saving..." : "Save changes"}
        </button>
      </div>
    </TaskDialog>
  );
}

function TaskDetailSkeleton() {
  return (
    <div className="space-y-6">
      <div className="task-detail-skeleton h-8 w-40" />
      <div className="task-detail-skeleton h-32" />
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="task-detail-skeleton h-40" />
        <div className="task-detail-skeleton h-40" />
      </div>
      <div className="task-detail-skeleton h-24" />
    </div>
  );
}

function TaskNotFound() {
  return (
    <div className="glass-card p-8 text-center">
      <h1 className="text-xl font-semibold text-white">Task not found</h1>
      <p className="mt-2 text-sm text-white/55">
        This task may have been removed or you may not have access to it.
      </p>
      <Link href="/dashboard/tasks" className="forge-button mt-6 inline-block w-auto px-6">
        Back to Founder Tasks
      </Link>
    </div>
  );
}
