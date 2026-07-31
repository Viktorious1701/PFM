/**
 * Transactions list — SKELETON.
 *
 * Out of scope for the current round. specs/001-user-onboarding/spec.md lists
 * "Features 03–11 (wallets, categories, budgets, transactions, reporting…)" as
 * explicitly excluded, and no spec exists for TM.
 */
import { Placeholder } from '../../../src/components/Placeholder';

export default function TransactionsScreen() {
  return (
    <Placeholder
      title="All Transactions"
      story="TM-US-02 (SRS §6 Feature-06) — not specified"
      endpoint="GET /api/v1/transactions"
      purpose="Paginated ledger of income and expense entries across every wallet, filterable by wallet, category and date range."
    />
  );
}
