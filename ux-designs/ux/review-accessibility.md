---
name: SamThuongShop — Accessibility Review
description: WCAG 2.1 AA review of the Sky & Sedge design + experience spines.
reviewer: Accessibility (WCAG 2.1 AA lens)
date: 2026-07-28
inputs:
  - ./DESIGN.md
  - ./EXPERIENCE.md
---

# Accessibility Review — SamThuongShop (WCAG 2.1 AA)

## Verdict

The palette's core claim holds **only for the surface it was tested on.** Every "deep"/text
token passes AA as text on **cream `#FBF9F4`** and on **white `#FFFFFF`** — that part of the
DESIGN.md claim is true and verified. But the contrast board was **never run against the
third background the system actually uses for text: `surface-sunken #F1EDE4`** — and on that
background the status-pill labels, the footer body text, and muted text all **fail AA**. Add
an invisible focus ring on the primary button, form-field borders below the 1.4.11 floor, and
missing focus-management/skip-link/required-field specs, and there is real remediation to do
before build.

Contrast method: WCAG 2.x relative-luminance ratio. Thresholds: **4.5:1** normal text,
**3.0:1** large text (≥24px, or ≥18.66px bold) and non-text UI components/graphics (1.4.11).
Caption type (13px/500) and body (16px) are **normal text → 4.5:1**.

---

## Contrast board (verified ratios)

### Text tokens on cream `#FBF9F4` — DESIGN.md claim CONFIRMED
| Token | Hex | Ratio | Normal (4.5) |
|---|---|---|---|
| ink | #3B4147 | **9.82:1** | PASS |
| ink-muted | #6B7178 | **4.69:1** | PASS (thin) |
| caption-deep | #71736B | **4.57:1** | PASS (thin) |
| sky-deep | #4C6577 | **5.81:1** | PASS |
| sage-deep | #5E6F4B | **5.18:1** | PASS |
| success | #4F7A52 | **4.71:1** | PASS (thin) |
| pending | #96681F | **4.65:1** | PASS (thin) |
| error | #A85248 | **5.03:1** | PASS |
| sky-soft | #7E9AAB | 2.81:1 | FAIL — correctly barred from text |
| sage-soft | #8B9B7A | 2.82:1 | FAIL — correctly barred from text |

### Text tokens on white `#FFFFFF` — CONFIRMED
ink 10.33 · ink-muted 4.93 · caption-deep 4.81 · sky-deep 6.11 · sage-deep 5.45 ·
success 4.96 · pending 4.89 · error 5.30 — **all PASS.** (soft variants 2.96/2.97 FAIL, correctly barred.)

### White text on colored fills — CONFIRMED
white on sky-deep **6.11** · on success **4.96** · on pending **4.89** · on error **5.30** —
**all PASS 4.5.** Primary-button hover `#3D5464` with white = **7.92** PASS.

### Text on `surface-sunken #F1EDE4` — NOT ON THE ORIGINAL BOARD; FAILURES FOUND
| Token (use) | Ratio on #F1EDE4 | Normal (4.5) |
|---|---|---|
| success (Paid pill label) | **4.24:1** | **FAIL** |
| pending (Awaiting pill label) | **4.18:1** | **FAIL** |
| ink-muted (footer body text) | **4.22:1** | **FAIL** |
| error (Cancelled pill label) | 4.53:1 | PASS (barely) |
| ink (footer links) | 8.84:1 | PASS |

Status **dots** (small graphic objects, 3.0 floor) do clear 3.0 on sunken (4.24/4.18/4.53),
so the dots are fine — it is the **word labels** that fail.

---

## Findings

### CRITICAL

**C1 — Primary-button focus ring is invisible (same color as the fill).** — DESIGN.md
`button-primary` ("focus shows a `{colors.sky-deep}` ring") + EXPERIENCE Accessibility Floor
("visible focus ring on all controls"). The button fill **is** sky-deep and the focus ring **is**
sky-deep → **1:1 contrast, no perceivable focus** on the single most important control (Add to
cart / Checkout / all primary CTAs). WCAG 2.4.7 (AA) and 1.4.11.
**Fix:** use a focus indicator that contrasts with the button itself — e.g. a 2px ring in
`ink #3B4147` **or** a white inner ring + sky-deep outer ring with a 2px offset (`outline-offset`),
so the indicator has ≥3:1 against both the button fill and the page. Specify a single global
focus-ring token that is never the same hue as the control it lands on.

### HIGH

**H1 — Status-pill labels fail AA on the pill background.** — DESIGN.md `status-pill`
(colored label on `surface-sunken #F1EDE4`). Paid/success **4.24:1** and Awaiting/pending
**4.18:1** are below 4.5 for the 13px caption label. WCAG 1.4.3. The Accessibility Floor's
blanket "all text/CTA tokens pass AA" is **false for this surface** — the board only tested cream.
**Fix (pick one):** (a) set the pill **label** in `ink #3B4147` (8.84:1) and keep color only in
the leading dot + a status icon; or (b) darken the status tokens (~ `success #3F6242`,
`pending #7E5717`) to clear 4.5 on #F1EDE4; or (c) drop the sunken background and put labels on
white. Re-run the board against **all three** backgrounds (cream, white, sunken).

**H2 — Footer body text fails AA.** — DESIGN.md `footer` (`text-color: ink-muted` on
`background: surface-sunken`). ink-muted on #F1EDE4 = **4.22:1**, below 4.5 for body/caption text.
WCAG 1.4.3.
**Fix:** use `ink #3B4147` for footer body copy (8.84:1), or reserve ink-muted for footer text
only on white. Do not put ink-muted, success, or pending as normal-size text on surface-sunken.

**H3 — Form-field border below the non-text contrast floor.** — DESIGN.md `text-input`
(`border: 1px {colors.border} #E4DFD3`). #E4DFD3 vs white = **1.33:1**, vs cream even lower —
far below the 3.0 required to identify a UI component's boundary. WCAG 1.4.11. Fields are not
reliably perceivable as inputs; only the (also-thin) focus border makes one field pop, and only
when focused. (The same hairline on **non-interactive** cards/photos is fine — 1.4.11 targets
interactive components and meaningful graphics.)
**Fix:** give interactive inputs a boundary ≥3:1 against their background (e.g. a darker input
border ~ `#9AA0A6`+), or add a filled input background distinct from the page. Keep the decorative
hairline for cards/photo frames.

**H4 — Focus trap + focus return specified for the lightbox only; missing for the other two
overlays.** — EXPERIENCE Interaction Primitives / Component Patterns. The **cart drawer** and the
**mobile hamburger menu** are transient overlays (they use `{shadows.overlay}`) but neither has a
documented focus trap or focus-restore-on-close; only the lightbox does. Nav dropdown likewise.
Keyboard/SR users will tab into the page behind an open drawer/menu. WCAG 2.4.3, 2.1.2.
**Fix:** state, for every overlay (cart drawer, mobile menu, nav dropdown, lightbox, any dialog):
move focus in on open, trap focus while open, `Esc` closes (already covered), and **restore focus
to the trigger** on close. Give each overlay a proper role (`dialog`/`aria-modal`) and accessible name.

**H5 — No required-field indication convention.** — EXPERIENCE Forms / State Patterns cover
labels, inline errors, aria-describedby, and focusing the first invalid field, but there is **no
spec for how a required field is marked before submission** (checkout, contact, login, address,
guest lookup). WCAG 3.3.2.
**Fix:** define a visible required marker that is not color/asterisk-alone — e.g. a "Required"
text tag or "(required)" in the label — plus `aria-required="true"` / `required`. Document the
optional-vs-required convention once, globally.

**H6 — No skip link and no landmark/heading-structure spec, with a sticky nav.** — EXPERIENCE
Accessibility Floor + Component Patterns (nav is "sticky on scroll"). Nothing in either spine
specifies a skip-to-content link, landmark regions (`header`/`nav`/`main`/`footer`), or a
single-`<h1>`/logical-heading rule. A sticky top nav plus no skip link forces keyboard users to
tab the full nav on every page. WCAG 2.4.1, 1.3.1, 2.4.6.
**Fix:** add a visible-on-focus "Skip to content" link as the first focusable element; wrap
regions in landmarks; require exactly one `<h1>` per surface and no skipped heading levels
(the type ramp defines sizes, not order). Ensure the sticky nav doesn't hide the target of an
in-page focus/anchor jump (`scroll-margin-top`).

### MEDIUM

**M1 — DESIGN.md and EXPERIENCE.md contradict each other on the status pill.** DESIGN.md
`status-pill`: "Color lives in the dot and text… on `surface-sunken`, never as a loud fill."
EXPERIENCE Component Patterns → Status pill: "**white text on a status fill**." These are two
different components with different contrast profiles. Per the spine's own precedence rule the
EXPERIENCE version (white-on-fill, which PASSES 4.89–6.11) wins — but the DESIGN token spec
(colored-on-sunken, which FAILS per H1) is what a developer reading DESIGN.md would build.
**Fix:** reconcile to one spec. If you keep colored-label-on-sunken, apply H1's fix; if you adopt
white-on-fill, update DESIGN.md `status-pill` and re-check the pending fill (white on pending
#96681F = 4.89, PASS).

**M2 — Variant selection state is conveyed by color alone.** — DESIGN.md `variant-selector`
(selected = sky-deep border + sky-deep label; unselected = border/ink). Both differentiators are
**color changes** on identically-shaped chips; a colorblind or low-vision user may not identify the
selected option. WCAG 1.4.1.
**Fix:** add a non-color selected cue — a checkmark, a filled/tinted background, or bold weight —
and expose it as a radio group (`role="radiogroup"`, `aria-checked`) with arrow-key selection.

**M3 — Language toggle: no accessible-state or keyboard/target spec, and likely sub-44px targets.**
— DESIGN.md `language-toggle` ("inline `EN | VN`… no box, a quiet text switch") + EXPERIENCE nav.
Active/inactive are shown by ink vs ink-muted color only; there's no `aria-current`/`aria-pressed`,
no focus-visible spec, and inline 13px text targets sit below the 44×44 floor the spine sets
elsewhere. WCAG 1.4.1, 2.5.5/2.5.8, 4.1.2, 2.4.7.
**Fix:** make each language a real button/link with a ≥44×44 hit area (padding, not glyph size),
`aria-current="true"` (or `aria-pressed`) on the active language, a visible focus ring, and an
accessible name that says the language ("English"/"Tiếng Việt", not just "EN"/"VN").

**M4 — Unavailable variant conveyed by muting (color) + non-interactivity.** — DESIGN.md
`variant-selector` ("Unavailable options are `ink-muted` and non-interactive"). The disabled
semantics help AT, but the *visual* distinction is color-only. WCAG 1.4.1 (minor; disabled
controls are contrast-exempt, but the available/unavailable distinction still shouldn't be color-only).
**Fix:** add a non-color cue for unavailable (strikethrough, "Unavailable" text, or a lock icon)
and ensure `disabled`/`aria-disabled`.

### LOW

**L1 — Thin passing margins on cream.** ink-muted 4.69, caption-deep 4.57, success 4.71, pending
4.65 all clear 4.5 but with almost no headroom; any future darkening of the cream, anti-aliasing,
or sub-pixel rendering on low-DPI screens erodes them. Not a defect — flag for the token owner to
avoid nudging these lighter, and to never place them on any surface darker than cream (see H1/H2).

**L2 — Alt-text convention is good; two edge cases to nail down.** EXPERIENCE covers
"{Species} — {location}", empty alt for decorative, and localization with the toggle — solid. Add:
(a) the lightbox "View this print"/"Xem bản in này" control needs an accessible name that includes
the product ("View this print — Common Kingfisher"), not a bare "View"; (b) confirm the
watermark-badge text ("WATERMARKED PREVIEW / XEM TRƯỚC") is live text or included in the image's
accessible name, not baked pixels only. (Blended badge #72767B on the preview gives white text
4.57:1 — PASS.)

**L3 — Reduced motion + i18n `lang` handling are well specified.** `prefers-reduced-motion`
(toast fade, lightbox transitions, no parallax/auto-motion), document-root `lang="vi"/"en"`
switching, per-node `lang="vi"` on Vietnamese fallback strings inside EN pages, and "test the
longer Vietnamese string first so layouts never break" are all present and correct. No change
needed — noted as verified so it isn't lost.

---

## Summary table

| ID | Sev | Location | WCAG | Status |
|---|---|---|---|---|
| C1 | Critical | button-primary focus ring | 2.4.7, 1.4.11 | ring == fill, invisible |
| H1 | High | status-pill labels on sunken | 1.4.3 | success 4.24 / pending 4.18 FAIL |
| H2 | High | footer body text on sunken | 1.4.3 | ink-muted 4.22 FAIL |
| H3 | High | text-input border | 1.4.11 | #E4DFD3 1.33 FAIL (3.0) |
| H4 | High | cart drawer / mobile menu focus | 2.4.3, 2.1.2 | trap+return unspecified |
| H5 | High | required-field indication | 3.3.2 | convention missing |
| H6 | High | skip link + landmarks + heading order | 2.4.1, 1.3.1 | unspecified, sticky nav |
| M1 | Medium | status-pill spec conflict | — | DESIGN vs EXPERIENCE |
| M2 | Medium | variant selected state | 1.4.1 | color-only |
| M3 | Medium | language toggle | 1.4.1, 2.5.5, 4.1.2 | state/kbd/target |
| M4 | Medium | variant unavailable state | 1.4.1 | color-only |
| L1 | Low | thin margins on cream | 1.4.3 | pass, monitor |
| L2 | Low | alt edge cases | 1.1.1 | lightbox/badge names |
| L3 | Low | motion + lang handling | — | verified good |
