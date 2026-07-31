/**
 * Create a wallet — SKELETON.
 *
 * Out of scope for the current round (SRS §6 Feature-03 / SDS §5.3.1 WM-US-01).
 */
import { Placeholder } from '../../../src/components/Placeholder';

export default function CreateWalletScreen() {
  return (
    <Placeholder
      title="Add Wallet"
      story="WM-US-01 (SRS §6 Feature-03) — not specified"
      endpoint="POST /api/v1/wallets"
      purpose="Name, type, currency and opening balance for a new wallet (SDS §6.2.1 WalletCreate)."
    />
  );
}
