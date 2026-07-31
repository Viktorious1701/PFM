/**
 * Stable element IDs for UI test selectors.
 *
 * specs/001-user-onboarding/plan.md records its Element IDs table as
 * `N/A (mobile deferred)`, and every `[UI]` row in test_cases.md is deferred to
 * "the mobile round". This registry gives those deferred rows real anchors so
 * that when the E2E pass is specified, the selectors already exist and are not
 * invented against a moving target.
 *
 * This file does NOT satisfy any TC. It is a registry, not a test.
 *
 * Rule: components reference these constants; no component hard-codes a testID
 * string. Renaming an ID here must be a deliberate, single-place change.
 */

export const InviteIds = {
  screen: 'invite-screen',
  emailInput: 'invite-email-input',
  emailError: 'invite-email-error',
  submit: 'invite-submit',
  successBanner: 'invite-success-banner',
  errorBanner: 'invite-error-banner',
  resultId: 'invite-result-id',
  resultEmail: 'invite-result-email',
  resultStatus: 'invite-result-status',
  resultExpiry: 'invite-result-expiry',
} as const;

export const LoginIds = {
  screen: 'login-screen',
  emailInput: 'login-email-input',
  passwordInput: 'login-password-input',
  submit: 'login-submit',
  errorBanner: 'login-error-banner',
} as const;

export const ActivateIds = {
  screen: 'activate-screen',
  fullNameInput: 'activate-full-name-input',
  passwordInput: 'activate-password-input',
  submit: 'activate-submit',
  successBanner: 'activate-success-banner',
  errorBanner: 'activate-error-banner',
} as const;

export const UsersIds = {
  screen: 'users-screen',
  list: 'users-list',
  row: (id: string) => `users-row-${id}`,
  statusChip: (id: string) => `users-status-${id}`,
  inviteCta: 'users-invite-cta',
} as const;

export const DashboardIds = {
  screen: 'dashboard-screen',
  netBalance: 'dashboard-net-balance',
  logTransactionCta: 'dashboard-log-transaction-cta',
  budgetAlert: 'dashboard-budget-alert',
} as const;
