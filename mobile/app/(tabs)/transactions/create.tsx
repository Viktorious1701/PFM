/**
 * Log a transaction — SKELETON.
 *
 * This is the screen UXR-01 constrains: logging an expense must take no more
 * than 3 taps and under 10 seconds. That budget is a design obligation for
 * whoever builds it, which is why it is recorded here rather than discovered
 * later. Out of scope for the current round (SRS §6 Feature-06).
 */
import { Placeholder } from '../../../src/components/Placeholder';

export default function CreateTransactionScreen() {
  return (
    <Placeholder
      title="Log Transaction"
      story="TM-US-01 (SRS §6 Feature-06) — not specified"
      endpoint="POST /api/v1/transactions"
      purpose="Quick-entry form for an expense or income: amount, wallet, category, note. Must satisfy UXR-01 — at most 3 taps, under 10 seconds — and update balances immediately (UXR-03)."
    />
  );
}
