/**
 * Wallets list — SKELETON.
 *
 * Out of scope for the current round (SRS §6 Feature-03 / SDS §5.3 WM).
 */
import { Placeholder } from '../../../src/components/Placeholder';

export default function WalletsScreen() {
  return (
    <Placeholder
      title="My Wallets"
      story="WM-US-02 (SRS §6 Feature-03) — not specified"
      endpoint="GET /api/v1/wallets"
      purpose="Every wallet the signed-in user owns with its current balance, plus the combined net total. Balances are DECIMAL(15,2) — never a float (constitution VL-07)."
    />
  );
}
