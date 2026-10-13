---
version: 1
slug: "mobile-app-tabs-transactions-index-tsx"
primary_target: "mobile/app/(tabs)/transactions/index.tsx"
related_targets: ["mobile/app/(tabs)/wallets/index.tsx","mobile/src/components/icons/NullscapesScene.tsx"]
---

## Direction contract

THESIS: A financial app's primary action shouldn't register as a weightless, smooth micro-interaction
the way every other finance app's "add" button does. Pressing "+ NEW SLIP" should feel like stamping a
moment into the ledger — visibly disrupting, then resettling. An empty state — nothing recorded yet —
reads as the aftermath of a blast, not a blank clipart illustration: the "null" the direction's own name
refers to.

OWN-WORLD (v5 — corrected against the user's own close reference, NULLSCAPESCRYO.png, after v3/v4 read
as a clean circular sun/planet rather than an explosion). The light source is now an irregular cluster
of overlapping blob shapes (not one circle), with a hot near-white off-center core inside a cooler wider
bloom, plus a tapering vertical beam escaping upward through a gap between two dark occluding wing
shapes at the top corners — this is what makes it read as "light escaping from behind something" rather
than a floating celestial body. Per the user's explicit instruction, the floating glass-cube debris
visible in their reference is NOT reproduced — only the background treatment. Flicker is now continuous
and irregular (a precomputed jittery keyframe sequence layered under the slower breathing pulse), not a
smooth sine alone — "capture the essence of flickering, like an explosion" was the user's own framing.
Fine static grain (a dense field of tiny low-opacity dots, distinct from the larger drifting debris) adds
the "broadcast corruption" texture visible across the whole reference image. A vignette darkens the
frame edges to match the reference's own contained, cornered-in composition. Spike colors shifted
cooler/steel-blue (farthest/far/near) to match the reference's palette more closely than the previous
near-black-only treatment.

STORY: Unchanged from v4 — an empty wallet/transaction list still states its own instruction in plain
text, the illustration is atmosphere behind it, never a replacement for it.

FIRST VIEWPORT: Same two call sites (app/(tabs)/wallets/index.tsx, app/(tabs)/transactions/index.tsx),
same `NullscapesScene` component. The glow/beam/wings are new static geometry; breathing + jitter
flicker, debris drift (3 groups), and the intermittent glitch burst (scanlines + near-spike jolt +
whole-scene flash) are all retained from v4, now driving the new explosion shape instead of the old
single circle. Reduce Motion still renders one static representative frame.

FORM: User-pinned direction, now in its third visual revision — each one a direct, explicit correction
from the user after seeing the previous build (too simple → grounded against the real Geometry Dash
level's documented behavior → "it's not a sun or a planet" corrected against a precise close reference
image). mode-operate.md's own DIRECTIONS/COMPS rules still bound this round — richer geometry and
texture, same placement (empty states only), no new surfaces added.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict,
DESIGN.md, and every shipping raster carrying its provenance.
