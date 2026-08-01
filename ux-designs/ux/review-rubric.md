# Spine Pair Review — SamThuongShop (Rubric Walk)

- **DESIGN.md:** `_bmad-output/planning-artifacts/ux-designs/ux-SamThuongShop-2026-07-18/DESIGN.md`
- **EXPERIENCE.md:** `_bmad-output/planning-artifacts/ux-designs/ux-SamThuongShop-2026-07-18/EXPERIENCE.md`
- **Source PRD:** `_bmad-output/planning-artifacts/prds/prd-SamThuongShop-2026-07-18/prd.md`
- **Reviewed:** 2026-07-28
- **Lens:** rubric walker (decision-readiness, coverage, spine discipline, coherence, flows/states, a11y posture)

## Gate verdict: **PASS-WITH-FIXES**

No Critical findings. The pair is a genuinely well-scoped lean UX: 13 surfaces close cleanly over the 25 FRs, the three flows mirror the PRD UJs with real climaxes, and the token spine is almost entirely resolvable. What holds it back from a clean PASS is **two direct DESIGN↔EXPERIENCE contradictions** (status-pill rendering; product-photo radius) that force a developer to guess and will produce inconsistent UI, plus **two missing failure-mode states** (search no-results, unavailable/unpublished product) that matter precisely because social links — a stated primary traffic source — can land on stale or empty results. All are surgical fixes; none is a rework.

---

## 1. Decision-readiness — **adequate**

A developer can build most of this without inventing decisions: tokens are concrete (real hex, a full type ramp, named spacing), the IA is a resolved sitemap, and each surface names its FRs and entry points. The gaps below are the specific places where the two contracts disagree or fall silent, forcing a guess.

### Findings
- **High** — **Status pill cannot be built from the pair; the two spines specify opposite renderings** (EXPERIENCE §Component Patterns "Status pill" line 106 vs DESIGN `components.status-pill` / §Components "status-pill"). EXPERIENCE says "Compact pill, **white text on a status fill**, with a leading dot." DESIGN says the pill sits on `{colors.surface-sunken}` with a **colored dot + colored label** and "**Color lives in the dot and text, never as a loud fill.**" These are mutually exclusive builds. *Fix:* reconcile to DESIGN's model (sunken background, colored dot + AA-safe colored label) and rewrite the EXPERIENCE line to "sunken pill, colored dot + colored label"; delete "white text on a status fill."
- **High** — **Product-card photo radius is contradicted** (EXPERIENCE §Component Patterns "Product card" line 101 says photo is `{rounded.md}`; DESIGN `product-card.image-radius` = `{rounded.sm}` and §Shapes locks photographs to 2px + hairline, with an explicit Don't: "DON'T round photographs like app thumbnails"). *Fix:* remove the radius from EXPERIENCE (it is a look decision DESIGN owns); the photo stays `{rounded.sm}` + hairline.
- **Medium** — **Shipped status has no dot/label color in the DESIGN component enumeration.** EXPERIENCE maps `{colors.info}` = Shipped (line 106) and `colors.info` exists (#4C6577), but `components.status-pill` lists only paid/awaiting/failed dot+label colors — a developer must infer the Shipped rendering. Shipped is a real status in the primary physical-print flow. *Fix:* add `shipped-dot`/`shipped-label-color: {colors.info}` to `status-pill`.

---

## 2. Coverage vs PRD — **strong**

Every customer-facing FR (FR-1–10, 13–18, 24, 25) has a landing surface and a reachable entry; the surface-closure map (EXPERIENCE §"Surface closure") is accurate and the operator-only FRs (11, 12, 19–23) are deliberately and correctly parked. The load-bearing PRD distinctions are all present: physical-vs-digital paths (variant selector shipping applicability), COD physical-only rule (checkout payment selector + Flow 1/2), bilingual VN-primary/EN-fallback (Foundation + i18n section), made-to-order/no-stock (state pattern + product card), re-download for guest and account (expired-link state), and email delivery of confirmation + download link (surface 7, digital-delivery-success state, Flow 1 step 7).

### Findings
- **Medium** — **Mixed-cart behavior (print + digital) is only implicit.** PRD FR-6 explicitly requires a mixed cart to take a shipping address and "ship only the print items"; FR-8 excludes COD from any cart with a digital item. The per-line shipping applicability + "disables COD for any cart containing a Digital Download" rules logically cover it, but no surface/flow/state names the mixed case or says how fulfillment splits (digital delivered on Paid while the print ships later). *Fix:* add one line to §Component Patterns "Checkout payment selector" or a mixed-cart note in State Patterns covering the split.
- **Low** — **Search (FR-3) is thin.** It appears only in the sitemap and surface 2's purpose; there is no component-pattern row or interaction primitive for the search input. Acceptable for a lean v1, but the no-results state (below) is the real gap.

---

## 3. Spine discipline — **adequate**

All `{path.to.token}` references in EXPERIENCE resolve to real DESIGN tokens by name — no dangling references. The one structural weakness is a **half-finished token migration**: the memlog records `pending-deep → pending` and `pending-soft` being dropped, but two EXPERIENCE sentences still read as if a soft/deep pair exists.

### Findings
- **Medium** — **`{colors.pending}` is referenced twice for two different roles, producing a meaningless sentence** (EXPERIENCE §Component Patterns line 106: "Large soft fills may use `{colors.pending}`, but pill text always uses the AA-safe `{colors.pending}`"; and §State Patterns intro line 112: "`{colors.pending}`/`{colors.pending}` (awaiting/processing)"). Both are leftovers from the retired soft/deep pending split — they now say "X but X." *Fix:* rewrite to the single `pending` token; drop the soft/deep distinction language.
- **Medium** — **Digital-tier vocabulary drifts between spines.** DESIGN `variant-selector` = "Web · Bản chuẩn · Độ phân giải cao / Web · **Standard** · **High-res**"; EXPERIENCE §Component Patterns line 102 = "Web / **Print-res** / **Full-res**" (and Flow 2 uses "Full-res"). Two different tier label sets for the same control. *Fix:* pick one set (VN + EN) and sync both spines.
- **Medium** — **EXPERIENCE restates DESIGN's visual composition for the product card** (line 101 re-specifies name typography, caption type+color, price type, tag color, and the photo radius). The Component Patterns table opens by declaring itself "Behavioral only — every visual spec … lives in `DESIGN.md.Components`," so this is the exact leak that produced the radius contradiction in §1. *Fix:* trim the row to behavior (one click target, no hover-only affordance, from-price shown); let DESIGN own the look.
- **Low** — **DESIGN carries several behavior statements** that belong in EXPERIENCE: `top-nav` "collapses to a hamburger," `language-toggle` "persists the choice across pages," `cart-line` "digital lines are locked to qty 1," `variant-selector` "unavailable options are non-interactive." All are duplicated (correctly) in EXPERIENCE, so this is redundancy/leak, not a conflict. *Fix:* optionally reduce DESIGN to visual state and keep behavior in EXPERIENCE, or accept as annotation.

---

## 4. Coherence — **adequate**

The locked direction holds across both files: Sky & Sedge, flat-editorial (hairline depth, one overlay shadow), unified peer nav (Home · Shop · Portfolio · About · Contact + cart + EN|VN), light-mode-only, bilingual VN-primary — all stated consistently in DESIGN §Brand & Style and EXPERIENCE §Foundation, matching the memlog decisions. The incoherences are local, not directional, and are the two High contradictions already logged in §1 (status-pill rendering; photo radius) plus the incomplete Shipped mapping (§1) and the tier-name drift (§3). No new coherence finding beyond those.

### Findings
- *(No additional findings — the coherence breaks are the cross-listed items in §1 and §3.)*
- **Low** — illustrative prices disagree across spines (DESIGN A3 = 1.250.000₫; EXPERIENCE Flow 1 A3 = 850.000₫) and "Order #" / "order number" / "Order reference" are used interchangeably within EXPERIENCE. Cosmetic; align examples and settle on the PRD's "Order" + "confirmation reference" wording.

---

## 5. Flows & states — **strong (flows); adequate (states)**

All three Key Flows are real and complete: named protagonist (Lan / Minh / a visitor, verbatim to PRD UJ-1/2/3), entry state, numbered steps, an explicit **CLIMAX** beat, a **Resolution**, and an **Edge case** — and each lists its surfaces and components. Flow 1 covers physical + Momo + guest + payment-abandon edge; Flow 2 covers digital + watermark + COD-hidden + link-expiry edge; Flow 3 covers portfolio→product conversion with the no-linked-product dead-end handled. This dimension is genuinely well done.

The 10 state patterns cover the payment matrix thoroughly (pending/bank-transfer, COD-processing, failed/abandoned, digital-success, expired→re-download) plus empty cart, image-heavy loading, made-to-order, form validation, and guest lookup. Two real failure modes are missing.

### Findings
- **Medium** — **No search no-results state.** FR-3 has a testable "entering a name returns matching Products"; the zero-match path (and search-in-progress) has no state pattern. *Fix:* add a "no results — try another name or browse Collections" state (never a dead end, per the empty-cart pattern's own principle).
- **Medium** — **No unavailable / unpublished-product / 404 state.** §State Patterns "Made-to-order availability" says "Unpublished Products simply do not appear," but social links (PRD §10, a primary traffic source) can point at a product the Operator later unpublishes (FR-19) or a bad URL. There is no "this print is no longer available" surface. *Fix:* add an unavailable-product state with a route back into Shop.
- **Low** — No generic request-failure state (e.g. add-to-cart or contact-submit server error) beyond the payment path. Acceptable for lean v1; a single generic error/toast pattern would close it.

---

## 6. Accessibility posture (spine level, structural only) — **adequate**

*(A dedicated a11y reviewer runs separately; these are structural gaps in the contract, not a full audit.)* The Accessibility Floor is strong for a lean spine: keyboard reachability + visible focus, tab-order-follows-reading-order, `Esc` closes topmost overlay, lightbox focus trap + restore, a bird-photo alt-text convention ("{Species} — {location}", empty alt for decorative), labels-not-placeholders with `aria-describedby` errors, 44×44 targets, `lang` root switching + per-node `lang` for VN fallback, and `prefers-reduced-motion`. DESIGN backs it with an AA contrast claim for all text/CTA tokens on cream.

### Findings
- **Medium (also feeds §1)** — **The "white text on a status fill" pill (EXPERIENCE line 106) is not backed by any contrast proof.** DESIGN proves deep tokens on the *cream* background, not white-on-success / white-on-pending / white-on-error fills. This is a second reason to resolve the pill contradiction toward DESIGN's proven sunken-bg + colored-text model. *Fix:* resolve per §1; if a fill were ever kept, DESIGN must add a white-on-fill contrast entry.
- **Medium** — **The add-to-cart toast has no screen-reader announcement.** §Interaction Primitives makes it "brief non-blocking," and reduced-motion drops the fade, but nothing states an `aria-live`/`role="status"` region — a non-visual user gets no add-to-cart confirmation. *Fix:* specify the toast (and cart-count change) is announced via a polite live region.
- **Low** — No skip-to-content link. Tab order is specified but a bypass mechanism for the persistent top nav is not. *Fix:* add a skip link to the Accessibility Floor.

---

## Mechanical notes

- **Frontmatter / inheritance:** EXPERIENCE `sources` → PRD path resolves; `design` → `./DESIGN.md` resolves. UJ names (UJ-1/2/3) and protagonist framing are verbatim from the PRD. Glossary terms (Product, Variant, Physical Print, Digital Download, Collection, Cart, Order, Order Status, Download Link, License, Payment Method) are used consistently and capitalized in EXPERIENCE.
- **Token migration residue:** the `pending-soft`/`pending-deep` → single `pending` rename (memlog 2026-07-18) is complete in DESIGN but left two dangling phrasings in EXPERIENCE (§3, lines 106 & 112).
- **Mermaid/ASCII:** the sitemap is a fenced ASCII tree, not Mermaid — renders fine, no syntax issue.
- **Visual reference coverage:** `mockups/`, `wireframes/`, `imports/` are empty — expected and defensible per the memlog decision ("Scope = customer-facing only … no mockups"). `.working/` holds the exploration HTML (three directions + palette + type specimen); these are process artifacts, not spine references, so no orphan-link finding. Spines-win-on-conflict is stated once (EXPERIENCE header).
- **Shape fit:** DESIGN sections are in canonical order (Brand & Style → Colors → Typography → Layout & Spacing → Elevation & Depth → Shapes → Components → Do's and Don'ts). EXPERIENCE carries all required defaults plus Responsive (triggered by multi-breakpoint) and an earned, clearly-tagged "Internationalization" invented section. Good.
```
