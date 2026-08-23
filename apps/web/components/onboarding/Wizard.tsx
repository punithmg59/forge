"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import {
  ApiError,
  confirmOnboarding,
  patchOnboardingDraft,
  structureOnboarding,
} from "@/lib/api";
import {
  OnboardingDraft,
  OnboardingPayload,
  STAGES,
  constraintText,
  normalizePayload,
  reviewRows,
  validateStep,
} from "@/lib/onboarding";

const TITLES = [
  "What are you building?",
  "Who are you building for?",
  "What matters right now?",
  "Give Forge more context",
  "Here's what Forge understands",
];

type SaveState = "idle" | "saving" | "saved" | "error";

export function OnboardingWizard({
  companyId,
  initialDraft,
}: {
  companyId: string;
  initialDraft: OnboardingDraft;
}) {
  const router = useRouter();
  const [step, setStep] = useState(Math.min(Math.max(initialDraft.current_step, 1), 5));
  const [payload, setPayload] = useState<OnboardingPayload>(
    normalizePayload(initialDraft.payload),
  );
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [error, setError] = useState("");
  const [aiMessage, setAiMessage] = useState("");
  const [structuring, setStructuring] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const saveSeq = useRef(0);
  const payloadRef = useRef(payload);
  const stepRef = useRef(step);

  useEffect(() => {
    payloadRef.current = payload;
  }, [payload]);

  useEffect(() => {
    stepRef.current = step;
  }, [step]);

  const persist = useCallback(
    async (nextPayload: OnboardingPayload, nextStep: number) => {
      const seq = ++saveSeq.current;
      setSaveState("saving");
      try {
        const constraint = constraintText(nextPayload);
        await patchOnboardingDraft(companyId, {
          current_step: nextStep,
          payload: {
            company: nextPayload.company,
            customer: {
              ...nextPayload.customer,
              beliefs: nextPayload.customer.problem
                ? [nextPayload.customer.problem]
                : nextPayload.customer.beliefs ?? [],
            },
            current_situation: {
              ...nextPayload.current_situation,
              constraint: constraint
                ? {
                    type: "other",
                    name: "onboarding_constraint",
                    description: constraint,
                    severity: "medium",
                  }
                : undefined,
            },
            context: nextPayload.context,
            ai_suggestion: nextPayload.ai_suggestion ?? null,
          },
        });
        if (seq === saveSeq.current) {
          setSaveState("saved");
        }
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          router.replace("/login");
          return;
        }
        if (seq === saveSeq.current) {
          setSaveState("error");
          setError(
            err instanceof ApiError
              ? err.message
              : "Unable to save. Your answers are still on this page.",
          );
        }
      }
    },
    [companyId, router],
  );

  const scheduleSave = useCallback(
    (nextPayload: OnboardingPayload, nextStep: number) => {
      if (saveTimer.current) {
        clearTimeout(saveTimer.current);
      }
      saveTimer.current = setTimeout(() => {
        void persist(nextPayload, nextStep);
      }, 650);
    },
    [persist],
  );

  useEffect(() => {
    return () => {
      if (saveTimer.current) {
        clearTimeout(saveTimer.current);
      }
    };
  }, []);

  function updatePayload(mutator: (current: OnboardingPayload) => OnboardingPayload) {
    setPayload((current) => {
      const next = mutator(current);
      scheduleSave(next, stepRef.current);
      return next;
    });
    setError("");
  }

  async function goNext() {
    const validation = validateStep(step, payload);
    if (validation) {
      setError(validation);
      return;
    }
    const nextStep = Math.min(step + 1, 5);
    setStep(nextStep);
    setError("");
    await persist(payload, nextStep);
  }

  async function goBack() {
    const nextStep = Math.max(step - 1, 1);
    setStep(nextStep);
    setError("");
    await persist(payload, nextStep);
  }

  async function onStructure() {
    setStructuring(true);
    setAiMessage("");
    setError("");
    try {
      await persist(payload, step);
      const result = await structureOnboarding(companyId);
      setPayload(normalizePayload(result.draft.payload));
      if (result.structured) {
        setAiMessage("Forge organized your notes. Review them before confirming.");
      } else {
        setAiMessage(
          result.error
            ? `AI unavailable (${result.error}). You can continue with your answers.`
            : "AI unavailable. You can continue with your answers.",
        );
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        router.replace("/login");
        return;
      }
      setAiMessage("AI unavailable. You can continue with your answers.");
    } finally {
      setStructuring(false);
    }
  }

  async function onConfirm() {
    if (confirming) {
      return;
    }
    setConfirming(true);
    setError("");
    try {
      await persist(payload, 5);
      await confirmOnboarding(companyId);
      router.replace("/dashboard");
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        router.replace("/login");
        return;
      }
      setError(
        err instanceof ApiError
          ? err.message
          : "Confirmation failed. Your draft is still saved.",
      );
      setConfirming(false);
    }
  }

  return (
    <div className="grid-bg relative min-h-screen overflow-hidden">
      <div
        className="orb orb-purple"
        style={{ width: 560, height: 560, top: "-140px", left: "-120px" }}
      />
      <div
        className="orb orb-blue"
        style={{ width: 480, height: 480, bottom: "-120px", right: "-100px" }}
      />
      <main className="relative z-10 mx-auto flex min-h-screen max-w-2xl flex-col px-6 py-10">
        <div className="mb-6 flex items-center justify-between gap-4">
          <div>
            <p className="text-xs font-semibold tracking-widest uppercase text-white/40">
              Forge · Onboarding
            </p>
            <p className="mt-1 text-sm text-white/50">
              Forge is learning how your company works.
            </p>
          </div>
          <p className="text-xs text-white/35" aria-live="polite">
            {saveState === "saving"
              ? "Saving..."
              : saveState === "saved"
                ? "Saved"
                : saveState === "error"
                  ? "Save failed"
                  : ""}
          </p>
        </div>

        <div className="mb-6 flex gap-2" aria-label="Onboarding progress">
          {[1, 2, 3, 4, 5].map((item) => (
            <div
              key={item}
              className={`h-1.5 flex-1 rounded-full ${
                item <= step ? "bg-violet-400" : "bg-white/10"
              }`}
            />
          ))}
        </div>

        <div className="glass-card flex-1 p-6 md:p-8">
          <p className="mb-2 text-xs tracking-widest uppercase text-white/35">
            Step {step} of 5
          </p>
          <h1 className="mb-6 text-2xl font-semibold">{TITLES[step - 1]}</h1>

          {step === 1 ? (
            <div className="space-y-4">
              <Field
                id="companyName"
                label="Company name"
                required
                example="Example: Forge"
                value={payload.company.name ?? ""}
                onChange={(value) =>
                  updatePayload((current) => ({
                    ...current,
                    company: { ...current.company, name: value },
                  }))
                }
              />
              <TextArea
                id="productDescription"
                label="Product description"
                required
                example="Example: An AI operating system for solo founders"
                value={payload.company.product_description ?? ""}
                onChange={(value) =>
                  updatePayload((current) => ({
                    ...current,
                    company: { ...current.company, product_description: value },
                  }))
                }
              />
              <div>
                <label className="forge-label" htmlFor="stage">
                  Stage <span className="text-violet-300">Required</span>
                </label>
                <select
                  id="stage"
                  className="forge-input"
                  value={payload.company.stage ?? "mvp"}
                  onChange={(event) =>
                    updatePayload((current) => ({
                      ...current,
                      company: { ...current.company, stage: event.target.value },
                    }))
                  }
                >
                  {STAGES.map((stage) => (
                    <option key={stage.value} value={stage.value}>
                      {stage.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          ) : null}

          {step === 2 ? (
            <div className="space-y-4">
              <Field
                id="targetCustomer"
                label="Target customer"
                required
                example="Example: Solo technical founders building SaaS products"
                value={payload.customer.target_customer ?? ""}
                onChange={(value) =>
                  updatePayload((current) => ({
                    ...current,
                    customer: { ...current.customer, target_customer: value },
                  }))
                }
              />
              <TextArea
                id="problem"
                label="Problem being solved"
                required
                example="Example: Founders lose context across tools and decisions"
                hint="This is your perspective — not a confirmed company fact yet."
                value={payload.customer.problem ?? ""}
                onChange={(value) =>
                  updatePayload((current) => ({
                    ...current,
                    customer: { ...current.customer, problem: value },
                  }))
                }
              />
            </div>
          ) : null}

          {step === 3 ? (
            <div className="space-y-4">
              <Field
                id="objective"
                label="Current objective"
                required
                example="Example: Get the first 20 paying customers"
                value={payload.current_situation.objective ?? ""}
                onChange={(value) =>
                  updatePayload((current) => ({
                    ...current,
                    current_situation: {
                      ...current.current_situation,
                      objective: value,
                    },
                  }))
                }
              />
              <TextArea
                id="bottleneck"
                label="Current bottleneck"
                required
                example="Example: Limited engineering bandwidth"
                value={payload.current_situation.bottleneck ?? ""}
                onChange={(value) =>
                  updatePayload((current) => ({
                    ...current,
                    current_situation: {
                      ...current.current_situation,
                      bottleneck: value,
                    },
                  }))
                }
              />
              <Field
                id="constraint"
                label="Constraint"
                optional
                example="Example: Stay under $4k monthly burn"
                value={constraintText(payload)}
                onChange={(value) =>
                  updatePayload((current) => ({
                    ...current,
                    current_situation: {
                      ...current.current_situation,
                      constraint: value,
                    },
                  }))
                }
              />
              <Field
                id="deadline"
                label="Deadline / urgency"
                optional
                example="Example: 2026-12-31"
                value={payload.current_situation.deadline ?? ""}
                onChange={(value) =>
                  updatePayload((current) => ({
                    ...current,
                    current_situation: {
                      ...current.current_situation,
                      deadline: value,
                    },
                  }))
                }
              />
            </div>
          ) : null}

          {step === 4 ? (
            <div className="space-y-4">
              <p className="text-sm text-white/45">
                Optional. Only add what you already know — do not invent strategy.
              </p>
              <TextArea
                id="mission"
                label="Mission"
                optional
                example="Example: Give every founder an AI co-founder"
                value={payload.context.mission ?? ""}
                onChange={(value) =>
                  updatePayload((current) => ({
                    ...current,
                    context: { ...current.context, mission: value },
                  }))
                }
              />
              <TextArea
                id="nonGoals"
                label="Non-goals"
                optional
                example="Example: Enterprise sales, multi-region compliance"
                value={payload.context.non_goals ?? ""}
                onChange={(value) =>
                  updatePayload((current) => ({
                    ...current,
                    context: { ...current.context, non_goals: value },
                  }))
                }
              />
            </div>
          ) : null}

          {step === 5 ? (
            <div className="space-y-4">
              <div className="space-y-3">
                {reviewRows(payload).map((row) => (
                  <div
                    key={row.label}
                    className="border-b border-white/5 pb-3 last:border-0"
                  >
                    <div className="mb-1 flex items-center justify-between gap-3">
                      <p className="forge-label mb-0">{row.label}</p>
                      <span className="text-[11px] text-white/35">{row.source}</span>
                    </div>
                    <p className="text-sm text-white/75">{row.value}</p>
                  </div>
                ))}
              </div>
              <button
                type="button"
                className="forge-button bg-none border border-white/15 bg-white/5"
                onClick={() => void onStructure()}
                disabled={structuring || confirming}
              >
                {structuring ? "Organizing..." : "Help me organize this"}
              </button>
              {aiMessage ? (
                <p className="text-sm text-white/50">{aiMessage}</p>
              ) : null}
            </div>
          ) : null}

          {error ? <p className="mt-4 text-sm text-red-400">{error}</p> : null}

          <div className="mt-8 flex gap-3">
            {step > 1 ? (
              <button
                type="button"
                className="forge-button w-auto min-w-28 bg-none border border-white/15 bg-white/5"
                onClick={() => void goBack()}
                disabled={confirming}
              >
                Back
              </button>
            ) : null}
            {step < 5 ? (
              <button
                type="button"
                className="forge-button"
                onClick={() => void goNext()}
              >
                Next
              </button>
            ) : (
              <>
                <button
                  type="button"
                  className="forge-button w-auto min-w-28 bg-none border border-white/15 bg-white/5"
                  onClick={() => setStep(1)}
                  disabled={confirming}
                >
                  Edit
                </button>
                <button
                  type="button"
                  className="forge-button"
                  onClick={() => void onConfirm()}
                  disabled={confirming}
                >
                  {confirming ? "Confirming..." : "Confirm Company Brain"}
                </button>
              </>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

function Field({
  id,
  label,
  value,
  onChange,
  example,
  required,
  optional,
  hint,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  example?: string;
  required?: boolean;
  optional?: boolean;
  hint?: string;
}) {
  return (
    <div>
      <label className="forge-label" htmlFor={id}>
        {label}{" "}
        {required ? <span className="text-violet-300">Required</span> : null}
        {optional ? <span className="text-white/35">Optional</span> : null}
      </label>
      <input
        id={id}
        className="forge-input"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
      {example ? <p className="mt-1 text-xs text-white/30">{example}</p> : null}
      {hint ? <p className="mt-1 text-xs text-white/40">{hint}</p> : null}
    </div>
  );
}

function TextArea({
  id,
  label,
  value,
  onChange,
  example,
  required,
  optional,
  hint,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  example?: string;
  required?: boolean;
  optional?: boolean;
  hint?: string;
}) {
  return (
    <div>
      <label className="forge-label" htmlFor={id}>
        {label}{" "}
        {required ? <span className="text-violet-300">Required</span> : null}
        {optional ? <span className="text-white/35">Optional</span> : null}
      </label>
      <textarea
        id={id}
        className="forge-input min-h-24"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
      {example ? <p className="mt-1 text-xs text-white/30">{example}</p> : null}
      {hint ? <p className="mt-1 text-xs text-white/40">{hint}</p> : null}
    </div>
  );
}
