/**
 * Money formatting and arithmetic over the wire's Decimal-as-string values.
 *
 * Every amount in this app arrives as a string (constitution VL-07; see
 * `api/types.ts`'s own convention note) — a `DECIMAL(15,2)` round-tripped
 * through `parseFloat`/`Number()` for arithmetic risks exactly the float
 * precision loss Decimal exists to avoid (`0.1 + 0.2 !== 0.3` in IEEE 754
 * double precision). Both functions below parse the sign/integer/fraction
 * parts of the string directly and do every addition in integer cents via
 * `bigint`; the only place a `Number` conversion happens is thousands-
 * grouping display in `formatMoney`, which is presentation, not arithmetic.
 */

/** `formatMoney`'s currency-symbol map. Anything else falls back to `"<CODE> "`. */
const CURRENCY_SYMBOLS: Record<string, string> = { USD: '$', EUR: '€', HKD: 'HK$' };

/**
 * Parses a Decimal-as-string wire value into integer cents as a `bigint` —
 * never a `Number`/`parseFloat` — so a 15-digit `DECIMAL(15,2)` amount is
 * never at risk of `Number.MAX_SAFE_INTEGER`'s ~16-digit ceiling. Accepts an
 * optional leading `-`, digits, and an optional fractional part of any
 * length; the fraction is padded or truncated to exactly 2 digits rather
 * than assuming the wire value always already has exactly 2 places.
 */
function parseCents(value: string): bigint {
  const match = /^(-)?(\d+)(?:\.(\d+))?$/.exec(value.trim());
  if (!match) {
    throw new Error(`Not a valid Decimal-as-string money value: "${value}"`);
  }
  const [, sign, whole, fraction = ''] = match;
  const centsPart = `${fraction}00`.slice(0, 2);
  const magnitude = BigInt(whole) * 100n + BigInt(centsPart);
  return sign ? -magnitude : magnitude;
}

/** Renders integer cents back to a fixed 2-decimal Decimal-as-string, e.g. `-105n` → `"-1.05"`. */
function formatCents(cents: bigint): string {
  const negative = cents < 0n;
  const abs = negative ? -cents : cents;
  const whole = abs / 100n;
  const frac = (abs % 100n).toString().padStart(2, '0');
  return `${negative ? '-' : ''}${whole}.${frac}`;
}

/**
 * Formats a Decimal-as-string amount with a currency symbol and thousands
 * grouping, e.g. `formatMoney('1250.75', 'USD')` → `"$1,250.75"`.
 *
 * `opts.signed` prefixes a non-negative result with `+` — used only by the
 * Reports screen's net-savings figure. Every other call site uses the
 * default unsigned form, where a negative value's own `-` sign is what
 * shows (never a doubled sign).
 */
export function formatMoney(value: string, currency: string, opts?: { signed?: boolean }): string {
  const cents = parseCents(value);
  const negative = cents < 0n;
  const abs = negative ? -cents : cents;
  const whole = abs / 100n;
  const frac = (abs % 100n).toString().padStart(2, '0');

  // Thousands grouping is display-only formatting, not arithmetic: `whole`
  // has already had its precision-sensitive fractional part split off, and
  // a DECIMAL(15,2)'s integer part (<= 13 digits) is far under
  // Number.MAX_SAFE_INTEGER, so this Number() conversion is safe.
  const groupedWhole = Number(whole).toLocaleString('en-US');
  const symbol = CURRENCY_SYMBOLS[currency] ?? `${currency} `;
  const sign = negative ? '-' : opts?.signed ? '+' : '';

  return `${sign}${symbol}${groupedWhole}.${frac}`;
}

/**
 * Sums Decimal-as-string amounts, integer-cents-safe throughout. Returns a
 * Decimal-as-string result so a caller can pass it straight back into
 * `formatMoney` (or into another `sumMoney` call). Does not check that every
 * value shares one currency — callers that mix currencies (e.g. a Wallets
 * folder with mixed-currency members) are expected to decide not to call
 * this at all, per DESIGN's "Mixed currencies" treatment.
 */
export function sumMoney(values: string[]): string {
  const total = values.reduce((sum, value) => sum + parseCents(value), 0n);
  return formatCents(total);
}
