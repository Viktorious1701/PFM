/** Display helpers shared by the pages. */

const DAY = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const MONTH = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

function sameDay(a: Date, b: Date) {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

/** "Today", "Yesterday", or "Wed 14 Oct" (plus the year when it isn't this one). */
export function dayLabel(iso: string, now = new Date()): string {
  const d = new Date(iso);
  if (sameDay(d, now)) return 'Today';
  const y = new Date(now);
  y.setDate(now.getDate() - 1);
  if (sameDay(d, y)) return 'Yesterday';
  return `${DAY[d.getDay()]} ${d.getDate()} ${MON[d.getMonth()]}${d.getFullYear() !== now.getFullYear() ? ` ${d.getFullYear()}` : ''}`;
}

/** Local day key for grouping, "2026-10-15". */
export function dayKey(iso: string): string {
  const d = new Date(iso);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

export function timeLabel(iso: string): string {
  const d = new Date(iso);
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

/** "October 2026" from an ISO date. */
export function monthLabel(isoDate: string): string {
  const [y, m] = isoDate.split('-').map(Number);
  return `${MONTH[m - 1]} ${y}`;
}

/** A typed amount, normalised to a Decimal-as-string ("12" -> "12.00"),
 * or null if it isn't one. Commas are tolerated as thousands separators.
 * For a whole-unit currency (VND) dots are thousands separators too, the
 * way amounts are written in Vietnam: "1.250.000" -> "1250000.00". */
export function parseAmount(input: string, { allowNegative = false, wholeUnits = false } = {}): string | null {
  if (wholeUnits) {
    // whole units only; dots or commas must be real thousands groups
    // ("1.250.000"), so a stray "12.5" is rejected rather than read as 125
    let w = input.replace(/[\s₫đ]/gi, '');
    const neg = w.startsWith('-');
    if (neg) w = w.slice(1);
    if (neg && !allowNegative) return null;
    if (!/^\d+$/.test(w) && !/^\d{1,3}([.,]\d{3})+$/.test(w)) return null;
    return `${neg ? '-' : ''}${w.replace(/[.,]/g, '').replace(/^0+(?=\d)/, '')}.00`;
  }
  const v = input.replace(/[\s,]/g, '').trim();
  const re = allowNegative ? /^-?\d+(\.\d{1,2})?$/ : /^\d+(\.\d{1,2})?$/;
  if (!re.test(v)) return null;
  const [whole, frac = ''] = v.split('.');
  return `${whole}.${frac.padEnd(2, '0')}`;
}

/** Input placeholder for an amount in `currency`. */
export function amountPlaceholder(currency: string): string {
  return currency === 'VND' ? '0' : '0.00';
}
