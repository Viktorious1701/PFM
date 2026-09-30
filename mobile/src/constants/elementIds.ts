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

export const ReportsIds = {
  screen: 'reports-screen',
  errorBanner: 'reports-error-banner',
  scale: 'reports-scale',
  netFigure: 'reports-net-figure',
  categoryStamp: (categoryId: string) => `reports-category-stamp-${categoryId}`,
} as const;

export const TransactionsIds = {
  screen: 'transactions-screen',
  list: 'transactions-list',
  slip: (id: string) => `transactions-slip-${id}`,
  filterWalletChip: 'transactions-filter-wallet-chip',
  filterCategoryChip: 'transactions-filter-category-chip',
  errorBanner: 'transactions-error-banner',
  fab: 'transactions-fab',
} as const;

export const TransactionCreateIds = {
  screen: 'transaction-create-screen',
  directionExpense: 'transaction-create-direction-expense',
  directionIncome: 'transaction-create-direction-income',
  amountInput: 'transaction-create-amount-input',
  amountError: 'transaction-create-amount-error',
  amountChip: (value: string) => `transaction-create-amount-chip-${value}`,
  walletTicket: (value: string) => `transaction-create-wallet-ticket-${value}`,
  walletError: 'transaction-create-wallet-error',
  categoryTicket: (value: string) => `transaction-create-category-ticket-${value}`,
  categoryError: 'transaction-create-category-error',
  noteInput: 'transaction-create-note-input',
  submit: 'transaction-create-submit',
  errorBanner: 'transaction-create-error-banner',
  newCategoryTrigger: 'transaction-create-new-category-trigger',
  newCategoryNameInput: 'transaction-create-new-category-name-input',
  newCategoryNameError: 'transaction-create-new-category-name-error',
  newCategorySubmit: 'transaction-create-new-category-submit',
} as const;

export const WalletsIds = {
  screen: 'wallets-screen',
  list: 'wallets-list',
  empty: 'wallets-empty',
  errorBanner: 'wallets-error-banner',
  addCta: 'wallets-add-cta',
  folder: (type: string) => `wallets-folder-${type}`,
  folderSubtotal: (type: string) => `wallets-folder-subtotal-${type}`,
  card: (id: string) => `wallets-card-${id}`,
} as const;

export const CreateWalletIds = {
  screen: 'create-wallet-screen',
  nameInput: 'create-wallet-name-input',
  nameError: 'create-wallet-name-error',
  typeInput: 'create-wallet-type-input',
  typeError: 'create-wallet-type-error',
  currencyInput: 'create-wallet-currency-input',
  currencyError: 'create-wallet-currency-error',
  balanceInput: 'create-wallet-balance-input',
  balanceError: 'create-wallet-balance-error',
  submit: 'create-wallet-submit',
  errorBanner: 'create-wallet-error-banner',
} as const;
