"use client";

/**
 * CompletenessBar — 0-100 completeness indicator.
 *
 * Spec (researchers-ui completeness display): shows a 0-100 indicator with
 * distinct complete/incomplete states. A profile is "complete" only at a
 * full score; anything less (e.g. 40) is incomplete.
 */

/** Complete threshold — a profile is complete only at a full 100 score. */
export const COMPLETE_THRESHOLD = 100;

/** Clamp a completeness score to the 0-100 range. */
export function clampScore(score: number): number {
  return Math.max(0, Math.min(100, Math.round(score)));
}

/** Resolve a score into a complete/incomplete state. */
export function getCompletenessState(score: number): "complete" | "incomplete" {
  return clampScore(score) >= COMPLETE_THRESHOLD ? "complete" : "incomplete";
}

interface CompletenessBarProps {
  score: number;
  className?: string;
}

/** Accessibility-friendly progress bar for a researcher's profile. */
export function CompletenessBar({ score, className }: CompletenessBarProps) {
  const clamped = clampScore(score);
  const state = getCompletenessState(score);
  const label = state === "complete" ? "Completo" : "Incompleto";

  return (
    <div
      className={className}
      role="progressbar"
      aria-valuenow={clamped}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label="Completitud del perfil"
    >
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>{label}</span>
        <span>{clamped}%</span>
      </div>
      <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-muted">
        <div
          className={`h-full rounded-full ${state === "complete" ? "bg-success" : "bg-warning"}`}
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  );
}
