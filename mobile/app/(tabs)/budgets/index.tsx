/**
 * Budget status — SKELETON.
 *
 * When built, this screen owns UXR-02: budget health must be readable from
 * colour alone (🟢 healthy · 🟡 warning · 🔴 exceeded). Those three states are
 * already defined in src/theme/tokens.ts (`color.budget`) with a `budgetHealth()`
 * helper, so the implementation does not get to invent its own thresholds.
 *
 * Out of scope for the current round (SRS §6 Feature-05 / SDS §5.5 BM).
 */
import { Placeholder } from '../../../src/components/Placeholder';

export default function BudgetsScreen() {
  return (
    <Placeholder
      title="Budget Status"
      story="BM-US-03 (SRS §6 Feature-05) — not specified"
      endpoint="GET /api/v1/budgets"
      purpose="Per-category budget progress with health conveyed by colour alone (UXR-02): green healthy, yellow at 80%, red over budget."
    />
  );
}
