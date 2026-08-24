"use client";

import { useCallback, useEffect, useState } from "react";

import { SectionCard } from "@/components/dashboard/SectionCard";
import {
  Approval,
  FounderTask,
  HeadAgentRecommendResponse,
  Objective,
  approveApproval,
  createApproval,
  listApprovals,
  listFounderTasks,
  listObjectives,
  rejectApproval,
  requestHeadAgentRecommendation,
  safeApiMessage,
} from "@/lib/api";
import {
  OPERATING_ERRORS,
  filterPendingApprovals,
  formatActionType,
  formatObjectiveMetric,
  formatTimestamp,
  hasPendingApprovalForAgentTask,
  isActionableRecommendation,
  objectiveTitleById,
} from "@/lib/operating";

const DEFAULT_QUESTION = "What should I focus on next?";

type OperatingViewProps = {
  companyId: string;
};

export function OperatingView({ companyId }: OperatingViewProps) {
  const [currentObjective, setCurrentObjective] = useState<Objective | null>(null);
  const [objectives, setObjectives] = useState<Objective[]>([]);
  const [objectiveLoading, setObjectiveLoading] = useState(true);
  const [objectiveError, setObjectiveError] = useState<string | null>(null);

  const [recommendation, setRecommendation] = useState<HeadAgentRecommendResponse | null>(
    null,
  );
  const [question, setQuestion] = useState(DEFAULT_QUESTION);
  const [recommendationLoading, setRecommendationLoading] = useState(false);
  const [recommendationError, setRecommendationError] = useState<string | null>(null);
  const [approvalRequestLoading, setApprovalRequestLoading] = useState(false);

  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [approvalsLoading, setApprovalsLoading] = useState(true);
  const [approvalsError, setApprovalsError] = useState<string | null>(null);
  const [approvalActionId, setApprovalActionId] = useState<string | null>(null);

  const [tasks, setTasks] = useState<FounderTask[]>([]);
  const [tasksLoading, setTasksLoading] = useState(true);
  const [tasksError, setTasksError] = useState<string | null>(null);

  const loadObjectives = useCallback(async () => {
    setObjectiveLoading(true);
    setObjectiveError(null);
    try {
      const response = await listObjectives(companyId);
      setObjectives(response.objectives);
      setCurrentObjective(response.current_objective);
    } catch (error) {
      setObjectiveError(safeApiMessage(error, OPERATING_ERRORS.objective));
    } finally {
      setObjectiveLoading(false);
    }
  }, [companyId]);

  const loadApprovals = useCallback(async () => {
    setApprovalsLoading(true);
    setApprovalsError(null);
    try {
      const response = await listApprovals(companyId);
      setApprovals(response.approvals);
    } catch (error) {
      setApprovalsError(safeApiMessage(error, OPERATING_ERRORS.approvals));
    } finally {
      setApprovalsLoading(false);
    }
  }, [companyId]);

  const loadTasks = useCallback(async () => {
    setTasksLoading(true);
    setTasksError(null);
    try {
      const response = await listFounderTasks(companyId);
      setTasks(response.tasks);
    } catch (error) {
      setTasksError(safeApiMessage(error, OPERATING_ERRORS.tasks));
    } finally {
      setTasksLoading(false);
    }
  }, [companyId]);

  useEffect(() => {
    void loadObjectives();
    void loadApprovals();
    void loadTasks();
  }, [loadObjectives, loadApprovals, loadTasks]);

  const pendingApprovals = filterPendingApprovals(approvals);

  async function onAskForge() {
    setRecommendationLoading(true);
    setRecommendationError(null);
    try {
      const response = await requestHeadAgentRecommendation(companyId, question.trim());
      setRecommendation(response);
    } catch (error) {
      setRecommendationError(safeApiMessage(error, OPERATING_ERRORS.recommendation));
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
      await createApproval(companyId, recommendation.agent_task_id);
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

  const canRequestApproval =
    recommendation?.agent_task_id &&
    isActionableRecommendation(recommendation.recommendation) &&
    !hasPendingApprovalForAgentTask(approvals, recommendation.agent_task_id);

  return (
    <div className="space-y-6">
      <SectionCard
        title="Current Objective"
        subtitle="The highest-priority active objective for this company."
        loading={objectiveLoading}
        error={objectiveError}
        empty={
          !currentObjective ? (
            <p>No active objective. Create one from your objective settings.</p>
          ) : undefined
        }
      >
        {currentObjective ? (
          <div className="space-y-3">
            <h2 className="text-xl font-semibold text-white">{currentObjective.title}</h2>
            {currentObjective.description ? (
              <p className="text-sm text-white/65">{currentObjective.description}</p>
            ) : null}
            <div className="grid gap-3 sm:grid-cols-2">
              <Meta label="Status" value={currentObjective.status} />
              <Meta label="Priority" value={String(currentObjective.priority)} />
              {formatObjectiveMetric(currentObjective) ? (
                <Meta
                  label="Success metric"
                  value={formatObjectiveMetric(currentObjective) ?? ""}
                />
              ) : null}
              {currentObjective.deadline ? (
                <Meta label="Deadline" value={currentObjective.deadline} />
              ) : null}
            </div>
          </div>
        ) : null}
      </SectionCard>

      <SectionCard
        title="Forge Recommendation"
        subtitle="A proposal from Forge — not a confirmed company fact."
        loading={recommendationLoading}
        error={recommendationError}
        empty={
          !recommendation ? (
            <div className="space-y-4">
              <p>No recommendation yet.</p>
              <div className="space-y-3">
                <label className="forge-label" htmlFor="forge-question">
                  Ask Forge
                </label>
                <input
                  id="forge-question"
                  className="forge-input"
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  placeholder={DEFAULT_QUESTION}
                />
                <button
                  className="forge-button w-auto px-5"
                  type="button"
                  disabled={recommendationLoading || !question.trim()}
                  onClick={() => void onAskForge()}
                >
                  Ask Forge
                </button>
              </div>
            </div>
          ) : undefined
        }
      >
        {recommendation ? (
          <RecommendationPanel
            data={recommendation}
            question={question}
            onQuestionChange={setQuestion}
            onAskForge={() => void onAskForge()}
            onRequestApproval={() => void onRequestApproval()}
            recommendationLoading={recommendationLoading}
            approvalRequestLoading={approvalRequestLoading}
            canRequestApproval={Boolean(canRequestApproval)}
          />
        ) : null}
      </SectionCard>

      <SectionCard
        title="Pending Approvals"
        subtitle="Review Forge proposals before they become founder tasks."
        loading={approvalsLoading}
        error={approvalsError}
        empty={
          pendingApprovals.length === 0 ? (
            <p>No pending approvals.</p>
          ) : undefined
        }
      >
        {pendingApprovals.length > 0 ? (
          <div className="space-y-4">
            {pendingApprovals.map((approval) => (
              <ApprovalCard
                key={approval.id}
                approval={approval}
                objectiveTitle={
                  currentObjective ? currentObjective.title : null
                }
                busy={approvalActionId === approval.id}
                onApprove={() => void onApprove(approval.id)}
                onReject={() => void onReject(approval.id)}
              />
            ))}
          </div>
        ) : null}
      </SectionCard>

      <SectionCard
        title="Founder Tasks"
        subtitle="Tasks created from approved Forge recommendations."
        loading={tasksLoading}
        error={tasksError}
        empty={tasks.length === 0 ? <p>No founder tasks yet.</p> : undefined}
      >
        {tasks.length > 0 ? (
          <div className="space-y-4">
            {tasks.map((task) => (
              <TaskCard
                key={task.id}
                task={task}
                objectiveTitle={objectiveTitleById(objectives, task.objective_id)}
              />
            ))}
          </div>
        ) : null}
      </SectionCard>
    </div>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="forge-label">{label}</p>
      <p className="text-sm text-white/70">{value}</p>
    </div>
  );
}

function RecommendationPanel({
  data,
  question,
  onQuestionChange,
  onAskForge,
  onRequestApproval,
  recommendationLoading,
  approvalRequestLoading,
  canRequestApproval,
}: {
  data: HeadAgentRecommendResponse;
  question: string;
  onQuestionChange: (value: string) => void;
  onAskForge: () => void;
  onRequestApproval: () => void;
  recommendationLoading: boolean;
  approvalRequestLoading: boolean;
  canRequestApproval: boolean;
}) {
  const rec = data.recommendation;
  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-violet-400/20 bg-violet-500/5 p-4">
        <p className="mb-1 text-xs uppercase tracking-widest text-violet-200/70">
          Proposal
        </p>
        <h3 className="text-lg font-semibold text-white">{rec.title}</h3>
        <p className="mt-2 text-sm text-white/75">{rec.recommendation}</p>
        <p className="mt-3 text-sm text-white/55">
          <span className="text-white/70">Rationale:</span> {rec.rationale}
        </p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <Meta label="Proposed action" value={formatActionType(rec.proposed_action.type)} />
        <Meta label="Confidence" value={rec.confidence} />
        {rec.proposed_action.title ? (
          <Meta label="Action title" value={rec.proposed_action.title} />
        ) : null}
        {rec.proposed_action.description ? (
          <Meta label="Action detail" value={rec.proposed_action.description} />
        ) : null}
      </div>
      {rec.sources.length > 0 ? (
        <div>
          <p className="forge-label">Sources</p>
          <ul className="mt-2 space-y-2">
            {rec.sources.map((source, index) => (
              <li
                key={`${source.entity_type}-${source.entity_id}-${index}`}
                className="rounded-lg border border-white/8 bg-white/3 px-3 py-2 text-sm text-white/65"
              >
                {source.entity_type ?? "source"}
                {source.entity_id ? ` · ${source.entity_id}` : ""}
                {source.source_type ? ` · ${source.source_type}` : ""}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      <div className="flex flex-col gap-3 sm:flex-row">
        {canRequestApproval ? (
          <button
            className="forge-button w-auto px-5"
            type="button"
            disabled={approvalRequestLoading}
            onClick={onRequestApproval}
          >
            {approvalRequestLoading ? "Submitting..." : "Request approval"}
          </button>
        ) : null}
      </div>
      <div className="border-t border-white/8 pt-4">
        <label className="forge-label" htmlFor="forge-question-followup">
          Ask Forge again
        </label>
        <div className="mt-2 flex flex-col gap-3 sm:flex-row">
          <input
            id="forge-question-followup"
            className="forge-input"
            value={question}
            onChange={(event) => onQuestionChange(event.target.value)}
          />
          <button
            className="forge-button w-auto px-5 sm:min-w-36"
            type="button"
            disabled={recommendationLoading || !question.trim()}
            onClick={onAskForge}
          >
            {recommendationLoading ? "Asking..." : "Ask Forge"}
          </button>
        </div>
      </div>
    </div>
  );
}

function ApprovalCard({
  approval,
  objectiveTitle,
  busy,
  onApprove,
  onReject,
}: {
  approval: Approval;
  objectiveTitle: string | null;
  busy: boolean;
  onApprove: () => void;
  onReject: () => void;
}) {
  return (
    <div className="rounded-xl border border-white/8 bg-white/3 p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-2">
          <h3 className="font-medium text-white">{approval.description}</h3>
          <p className="text-sm text-white/55">
            {formatActionType(approval.action_type)} · Risk {approval.risk_level}
          </p>
          <p className="text-xs text-white/40">
            Requested {formatTimestamp(approval.requested_at)}
          </p>
          {objectiveTitle ? (
            <p className="text-sm text-white/50">Objective: {objectiveTitle}</p>
          ) : null}
        </div>
        <div className="flex gap-2">
          <button
            className="rounded-lg border border-emerald-400/30 bg-emerald-500/10 px-4 py-2 text-sm font-medium text-emerald-200"
            type="button"
            disabled={busy}
            onClick={onApprove}
          >
            {busy ? "Working..." : "Approve"}
          </button>
          <button
            className="rounded-lg border border-white/12 bg-white/5 px-4 py-2 text-sm font-medium text-white/75"
            type="button"
            disabled={busy}
            onClick={onReject}
          >
            Reject
          </button>
        </div>
      </div>
    </div>
  );
}

function TaskCard({
  task,
  objectiveTitle,
}: {
  task: FounderTask;
  objectiveTitle: string | null;
}) {
  return (
    <div className="rounded-xl border border-white/8 bg-white/3 p-4">
      <h3 className="font-medium text-white">{task.title}</h3>
      {task.description ? (
        <p className="mt-2 text-sm text-white/65">{task.description}</p>
      ) : null}
      <div className="mt-3 grid gap-2 text-sm text-white/55 sm:grid-cols-3">
        <span>Status: {task.status}</span>
        <span>Priority: {task.priority}</span>
        {objectiveTitle ? <span>Objective: {objectiveTitle}</span> : null}
      </div>
    </div>
  );
}
