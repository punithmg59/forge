"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { AttentionPanel } from "@/components/dashboard/AttentionPanel";
import { BrainSummaryPanel } from "@/components/dashboard/BrainSummaryPanel";
import { CurrentObjectiveCard } from "@/components/dashboard/CurrentObjectiveCard";
import { FocusTasksPanel } from "@/components/dashboard/FocusTasksPanel";
import { ForgeRecommendationPanel } from "@/components/dashboard/ForgeRecommendationPanel";
import { OperatingLoopPanel } from "@/components/dashboard/OperatingLoopPanel";
import { RecentExecutionPanel } from "@/components/dashboard/RecentExecutionPanel";
import { SectionCard } from "@/components/dashboard/SectionCard";
import { TaskDialog } from "@/components/tasks/TaskDialog";
import {
  ApiError,
  type CompanyLearning,
  type FounderTask,
  type HeadAgentRecommendResponse,
  type Objective,
  approveApproval,
  correctLearning,
  createApproval,
  listApprovals,
  listFounderTasks,
  listLearnings,
  listObjectives,
  rejectApproval,
  requestHeadAgentRecommendation,
  safeApiMessage,
} from "@/lib/api";
import {
  buildOperatingLoopState,
  FOUNDER_DASHBOARD_EMPTY,
  selectActiveLearnings,
  selectBlockedTasks,
  selectFocusTasks,
  selectRecentCompletedTasks,
} from "@/lib/founder-dashboard";
import {
  OPERATING_ERRORS,
  filterPendingApprovals,
  formatLearningStatus,
  formatTimestamp,
  hasPendingApprovalForAgentTask,
  isActionableRecommendation,
  mapRecommendationApiError,
} from "@/lib/operating";
import { enrichTasksWithObjectives } from "@/lib/task-workspace";

const DEFAULT_QUESTION = "What should I focus on next?";

type FounderCommandCenterProps = {
  companyId: string;
};

export function FounderCommandCenter({ companyId }: FounderCommandCenterProps) {
  const [currentObjective, setCurrentObjective] = useState<Objective | null>(null);
  const [objectives, setObjectives] = useState<Objective[]>([]);
  const [objectiveLoading, setObjectiveLoading] = useState(true);
  const [objectiveError, setObjectiveError] = useState<string | null>(null);

  const [recommendation, setRecommendation] = useState<HeadAgentRecommendResponse | null>(null);
  const [question, setQuestion] = useState(DEFAULT_QUESTION);
  const [recommendationLoading, setRecommendationLoading] = useState(false);
  const [recommendationError, setRecommendationError] = useState<string | null>(null);
  const [approvalRequestLoading, setApprovalRequestLoading] = useState(false);

  const [approvals, setApprovals] = useState<Awaited<ReturnType<typeof listApprovals>>["approvals"]>([]);
  const [approvalsLoading, setApprovalsLoading] = useState(true);
  const [approvalsError, setApprovalsError] = useState<string | null>(null);
  const [approvalActionId, setApprovalActionId] = useState<string | null>(null);

  const [tasks, setTasks] = useState<FounderTask[]>([]);
  const [tasksLoading, setTasksLoading] = useState(true);
  const [tasksError, setTasksError] = useState<string | null>(null);

  const [learnings, setLearnings] = useState<CompanyLearning[]>([]);
  const [learningsLoading, setLearningsLoading] = useState(true);
  const [learningsError, setLearningsError] = useState<string | null>(null);
  const [correctingLearning, setCorrectingLearning] = useState<CompanyLearning | null>(null);
  const [correctionReason, setCorrectionReason] = useState("");
  const [correctionLoading, setCorrectionLoading] = useState(false);
  const [correctionError, setCorrectionError] = useState<string | null>(null);

  const resetCompanyState = useCallback(() => {
    setCurrentObjective(null);
    setObjectives([]);
    setRecommendation(null);
    setQuestion(DEFAULT_QUESTION);
    setRecommendationError(null);
    setApprovals([]);
    setTasks([]);
    setLearnings([]);
    setObjectiveError(null);
    setApprovalsError(null);
    setTasksError(null);
    setLearningsError(null);
    setCorrectingLearning(null);
    setCorrectionReason("");
    setCorrectionError(null);
  }, []);

  const loadObjectives = useCallback(async () => {
    const requestedCompanyId = companyId;
    setObjectiveLoading(true);
    setObjectiveError(null);
    try {
      const response = await listObjectives(requestedCompanyId);
      if (requestedCompanyId !== companyId) {
        return;
      }
      setObjectives(response.objectives);
      setCurrentObjective(response.current_objective);
    } catch (error) {
      if (requestedCompanyId !== companyId) {
        return;
      }
      setObjectiveError(safeApiMessage(error, OPERATING_ERRORS.objective));
    } finally {
      if (requestedCompanyId === companyId) {
        setObjectiveLoading(false);
      }
    }
  }, [companyId]);

  const loadApprovals = useCallback(async () => {
    const requestedCompanyId = companyId;
    setApprovalsLoading(true);
    setApprovalsError(null);
    try {
      const response = await listApprovals(requestedCompanyId);
      if (requestedCompanyId !== companyId) {
        return;
      }
      setApprovals(response.approvals);
    } catch (error) {
      if (requestedCompanyId !== companyId) {
        return;
      }
      setApprovalsError(safeApiMessage(error, OPERATING_ERRORS.approvals));
    } finally {
      if (requestedCompanyId === companyId) {
        setApprovalsLoading(false);
      }
    }
  }, [companyId]);

  const loadTasks = useCallback(async () => {
    const requestedCompanyId = companyId;
    setTasksLoading(true);
    setTasksError(null);
    try {
      const response = await listFounderTasks(requestedCompanyId);
      if (requestedCompanyId !== companyId) {
        return;
      }
      setTasks(response.tasks);
    } catch (error) {
      if (requestedCompanyId !== companyId) {
        return;
      }
      setTasksError(safeApiMessage(error, OPERATING_ERRORS.tasks));
    } finally {
      if (requestedCompanyId === companyId) {
        setTasksLoading(false);
      }
    }
  }, [companyId]);

  const loadLearnings = useCallback(async () => {
    const requestedCompanyId = companyId;
    setLearningsLoading(true);
    setLearningsError(null);
    try {
      const response = await listLearnings(requestedCompanyId);
      if (requestedCompanyId !== companyId) {
        return;
      }
      setLearnings(response.learnings);
    } catch (error) {
      if (requestedCompanyId !== companyId) {
        return;
      }
      setLearningsError(safeApiMessage(error, OPERATING_ERRORS.brain));
    } finally {
      if (requestedCompanyId === companyId) {
        setLearningsLoading(false);
      }
    }
  }, [companyId]);

  useEffect(() => {
    resetCompanyState();
    void Promise.all([
      loadObjectives(),
      loadApprovals(),
      loadTasks(),
      loadLearnings(),
    ]);
  }, [companyId, resetCompanyState, loadObjectives, loadApprovals, loadTasks, loadLearnings]);

  const enrichedTasks = useMemo(
    () => enrichTasksWithObjectives(tasks, objectives),
    [tasks, objectives],
  );
  const pendingApprovals = filterPendingApprovals(approvals);
  const blockedTasks = useMemo(() => selectBlockedTasks(enrichedTasks), [enrichedTasks]);
  const focusTasks = useMemo(() => selectFocusTasks(enrichedTasks), [enrichedTasks]);
  const recentCompleted = useMemo(() => selectRecentCompletedTasks(tasks), [tasks]);
  const activeLearnings = useMemo(() => selectActiveLearnings(learnings), [learnings]);

  const operatingLoopStages = useMemo(
    () =>
      buildOperatingLoopState({
        hasObjective: currentObjective !== null,
        hasPendingApprovals: pendingApprovals.length > 0,
        hasTasks: tasks.some((task) => task.status !== "completed"),
        hasCompletedTasks: recentCompleted.length > 0,
        hasLearnings: learnings.length > 0,
        hasActiveLearnings: activeLearnings.length > 0,
      }),
    [
      currentObjective,
      pendingApprovals.length,
      tasks,
      recentCompleted.length,
      learnings.length,
      activeLearnings.length,
    ],
  );

  const attentionLoading =
    approvalsLoading &&
    tasksLoading &&
    pendingApprovals.length === 0 &&
    blockedTasks.length === 0;

  const canRequestApproval =
    recommendation?.agent_task_id &&
    isActionableRecommendation(recommendation.recommendation) &&
    !hasPendingApprovalForAgentTask(approvals, recommendation.agent_task_id);

  async function onAskForge() {
    if (recommendationLoading || !question.trim()) {
      return;
    }
    setRecommendationLoading(true);
    setRecommendationError(null);
    try {
      const response = await requestHeadAgentRecommendation(companyId, question.trim());
      setRecommendation(response);
    } catch (error) {
      if (error instanceof ApiError) {
        setRecommendationError(mapRecommendationApiError(error.message, error.status));
      } else {
        setRecommendationError(safeApiMessage(error, OPERATING_ERRORS.recommendation));
      }
    } finally {
      setRecommendationLoading(false);
    }
  }

  async function onRequestApproval() {
    if (!recommendation?.agent_task_id) {
      return;
    }
    setApprovalRequestLoading(true);
    try {
      await createApproval(companyId, { agent_task_id: recommendation.agent_task_id });
      await loadApprovals();
    } catch (error) {
      setRecommendationError(safeApiMessage(error, OPERATING_ERRORS.approvalAction));
    } finally {
      setApprovalRequestLoading(false);
    }
  }

  async function onApprove(approvalId: string) {
    setApprovalActionId(approvalId);
    try {
      await approveApproval(companyId, approvalId);
      await Promise.all([loadApprovals(), loadTasks()]);
    } catch (error) {
      setApprovalsError(safeApiMessage(error, OPERATING_ERRORS.approvalAction));
    } finally {
      setApprovalActionId(null);
    }
  }

  async function onReject(approvalId: string) {
    setApprovalActionId(approvalId);
    try {
      await rejectApproval(companyId, approvalId);
      await loadApprovals();
    } catch (error) {
      setApprovalsError(safeApiMessage(error, OPERATING_ERRORS.approvalAction));
    } finally {
      setApprovalActionId(null);
    }
  }

  async function onSubmitCorrection() {
    if (!correctingLearning) {
      return;
    }
    setCorrectionLoading(true);
    setCorrectionError(null);
    try {
      await correctLearning(companyId, correctingLearning.id, correctionReason.trim());
      setCorrectingLearning(null);
      setCorrectionReason("");
      await loadLearnings();
    } catch (error) {
      setCorrectionError(safeApiMessage(error, OPERATING_ERRORS.brain));
    } finally {
      setCorrectionLoading(false);
    }
  }

  return (
    <div className="space-y-8">
      <CurrentObjectiveCard
        objective={currentObjective}
        loading={objectiveLoading}
        error={objectiveError}
        onRetry={() => void loadObjectives()}
      />

      <AttentionPanel
        pendingApprovals={pendingApprovals}
        blockedTasks={blockedTasks}
        objectiveTitle={currentObjective?.title ?? null}
        loading={attentionLoading}
        error={approvalsError}
        approvalActionId={approvalActionId}
        onRetry={() => void loadApprovals()}
        onApprove={(id) => void onApprove(id)}
        onReject={(id) => void onReject(id)}
      />

      <div className="grid gap-8 lg:grid-cols-3">
        <div className="space-y-8 lg:col-span-2">
          <FocusTasksPanel
            tasks={focusTasks}
            loading={tasksLoading}
            error={tasksError}
            onRetry={() => void loadTasks()}
          />
          <RecentExecutionPanel
            tasks={recentCompleted}
            loading={tasksLoading}
            error={tasksError}
            onRetry={() => void loadTasks()}
          />
        </div>

        <div className="space-y-8">
          <SectionCard
            title="Forge recommendation"
            subtitle="On-demand proposal — not company truth until approved."
            loading={false}
            error={null}
            empty={
              !recommendation && !recommendationError && !recommendationLoading
                ? <p>{FOUNDER_DASHBOARD_EMPTY.recommendation}</p>
                : undefined
            }
          >
            <ForgeRecommendationPanel
              recommendation={recommendation}
              recommendationError={recommendationError}
              question={question}
              recommendationLoading={recommendationLoading}
              approvalRequestLoading={approvalRequestLoading}
              canRequestApproval={Boolean(canRequestApproval)}
              onQuestionChange={setQuestion}
              onAskForge={() => void onAskForge()}
              onRequestApproval={() => void onRequestApproval()}
            />
          </SectionCard>

          <BrainSummaryPanel
            activeLearnings={activeLearnings}
            loading={learningsLoading}
            error={learningsError}
            onRetry={() => void loadLearnings()}
          />
        </div>
      </div>

      <OperatingLoopPanel stages={operatingLoopStages} />

      <SectionCard
        id="company-brain"
        title="Company Brain knowledge"
        subtitle="Full learning history with provenance. Only active learnings are current company truth."
        loading={learningsLoading}
        error={learningsError}
        onRetry={() => void loadLearnings()}
        empty={learnings.length === 0 ? <p>{FOUNDER_DASHBOARD_EMPTY.brain}</p> : undefined}
      >
        {learnings.length > 0 ? (
          <div className="space-y-4">
            {learnings.map((learning) => (
              <LearningBrainCard
                key={learning.id}
                learning={learning}
                onMarkOutdated={() => {
                  setCorrectingLearning(learning);
                  setCorrectionReason("");
                  setCorrectionError(null);
                }}
              />
            ))}
          </div>
        ) : null}
      </SectionCard>

      {correctingLearning ? (
        <TaskDialog
          open={correctingLearning !== null}
          title="Mark as outdated"
          onClose={() => setCorrectingLearning(null)}
        >
          <p className="text-sm text-white/65">
            This will remove this learning from current Company Brain knowledge. Evidence remains.
          </p>
          <label className="mt-4 block text-sm text-white/70" htmlFor="correction-reason">
            Why is this outdated?
          </label>
          <textarea
            id="correction-reason"
            className="forge-input mt-2 min-h-[100px]"
            value={correctionReason}
            onChange={(event) => setCorrectionReason(event.target.value)}
            placeholder="Customer interviews were from an outdated market segment."
          />
          {correctionError ? (
            <p className="mt-2 text-sm text-red-300">{correctionError}</p>
          ) : null}
          <div className="mt-4 flex justify-end gap-2">
            <button
              className="forge-button-secondary"
              type="button"
              disabled={correctionLoading}
              onClick={() => setCorrectingLearning(null)}
            >
              Cancel
            </button>
            <button
              className="rounded-lg border border-amber-400/30 bg-amber-500/10 px-4 py-2 text-sm font-medium text-amber-100"
              type="button"
              disabled={correctionLoading || correctionReason.trim().length === 0}
              onClick={() => void onSubmitCorrection()}
            >
              {correctionLoading ? "Saving..." : "Confirm"}
            </button>
          </div>
        </TaskDialog>
      ) : null}
    </div>
  );
}

function LearningBrainCard({
  learning,
  onMarkOutdated,
}: {
  learning: CompanyLearning;
  onMarkOutdated: () => void;
}) {
  const statusLabel = formatLearningStatus(learning.status);
  const statusClass =
    learning.status === "active"
      ? "text-emerald-200 border-emerald-400/30 bg-emerald-500/10"
      : learning.status === "proposed"
        ? "text-amber-200 border-amber-400/30 bg-amber-500/10"
        : "text-white/60 border-white/12 bg-white/5";

  return (
    <article className="rounded-xl border border-white/8 bg-white/3 p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-2 min-w-0">
          <span
            className={`inline-block rounded-full border px-2 py-0.5 text-xs font-medium uppercase tracking-wide ${statusClass}`}
          >
            {statusLabel}
          </span>
          <p className="text-sm text-white/85">{learning.statement}</p>
          {learning.evidence_summary ? (
            <p className="text-xs text-white/50">Reason: {learning.evidence_summary}</p>
          ) : null}
          {learning.provenance?.objective_task_title ? (
            <p className="text-xs text-white/45">Task: {learning.provenance.objective_task_title}</p>
          ) : null}
          <p className="text-xs text-white/35">Created {formatTimestamp(learning.created_at)}</p>
        </div>
        {learning.status === "active" ? (
          <button
            className="rounded-lg border border-amber-400/30 bg-amber-500/10 px-4 py-2 text-sm font-medium text-amber-100 shrink-0"
            type="button"
            onClick={onMarkOutdated}
          >
            Mark as outdated
          </button>
        ) : null}
      </div>
    </article>
  );
}
