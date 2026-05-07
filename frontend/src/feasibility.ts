// Rule-based feasibility heuristic for the New Goal flow.
// Keeps logic instant and offline; the AI has the final say on goal detail screen.
export type Feasibility = 'ok' | 'tight' | 'unrealistic';
export type FeasibilityResult = { level: Feasibility; reasonKey: string | null; suggestedDays: number };

export function evaluateFeasibility(opts: {
  deadline: string; // YYYY-MM-DD
  hoursPerWeek: number;
  level: 'beginner' | 'intermediate' | 'advanced' | string;
}): FeasibilityResult {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const due = new Date(opts.deadline + 'T00:00:00');
  const days = Math.max(0, Math.round((due.getTime() - today.getTime()) / 86400000));
  const weeks = Math.max(1, Math.ceil(days / 7));
  const totalHours = opts.hoursPerWeek * weeks;

  // Hard floors
  if (days < 7) return { level: 'unrealistic', reasonKey: 'feas_reason_under_week', suggestedDays: 30 };
  if (totalHours < 5) return { level: 'unrealistic', reasonKey: 'feas_reason_too_few_hours', suggestedDays: Math.max(30, Math.ceil(20 / Math.max(1, opts.hoursPerWeek)) * 7) };

  // Per-level thresholds (rough defaults)
  const minHoursOk: Record<string, number> = { beginner: 30, intermediate: 20, advanced: 10 };
  const minHoursTight: Record<string, number> = { beginner: 15, intermediate: 10, advanced: 5 };
  const okFloor = minHoursOk[opts.level] ?? 20;
  const tightFloor = minHoursTight[opts.level] ?? 10;

  if (totalHours < tightFloor) {
    const targetHours = okFloor;
    const targetDays = Math.ceil(targetHours / Math.max(1, opts.hoursPerWeek)) * 7;
    return { level: 'unrealistic', reasonKey: 'feas_reason_short_for_level', suggestedDays: targetDays };
  }
  if (totalHours < okFloor) {
    const targetHours = okFloor;
    const targetDays = Math.ceil(targetHours / Math.max(1, opts.hoursPerWeek)) * 7;
    return { level: 'tight', reasonKey: 'feas_reason_tight', suggestedDays: targetDays };
  }
  return { level: 'ok', reasonKey: null, suggestedDays: days };
}

export function addDays(days: number): string {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}
