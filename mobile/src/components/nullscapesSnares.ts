/**
 * Snare-hit times (ms) in the song (official version; the app plays its
 * first 1:33.5 as a loop, see SONG_MS),
 * used to fire the scene's flash in sync with the song. Generated offline:
 * percussive component (HPSS) -> 1.5-5 kHz onset flux on a 129 BPM beat
 * grid. The snare's beat within the bar is picked per bar from the
 * surrounding 8 bars, because the song shifts it by one beat around
 * 105-120s (beat 3 before, beat 4 after). A bar only gets a flash when that
 * beat's snare clearly stands out (>=1.25x the bar's other beats), so
 * breakdowns, the outro, and the busiest drum passages are skipped rather
 * than guessed. Each time is snapped to the actual onset peak.
 */
export const SNARE_MS: readonly number[] = [4679, 6560, 8429, 10310, 12190, 14060, 15929, 19691, 21560, 23429, 25310, 27191, 29060, 30929, 34691, 36560, 38429, 40310, 42191, 44060, 45929, 49691, 51560, 55310, 57191, 59095, 62810, 64691, 66560, 70310, 72191, 74060, 75929, 77810, 79679, 81560, 83429, 85310, 87191, 89060, 90929, 94679, 98429, 100322, 102191, 104060, 105929, 107578, 109447, 111328, 114614, 117191, 119060, 120941, 122810, 124691, 126560, 128441, 130322, 132191, 134060, 135941, 137822, 141560, 143441, 145310, 154680, 156561, 158441, 160311, 162180, 167845, 169680, 173430, 175345, 179061, 180965, 182846, 184680, 186561, 188465, 190311, 192180, 194061, 195942, 197822, 199692, 201561];

/**
 * The climax: from the crash cymbal at 63.72 s (a high-band spike ~20 dB
 * over the surrounding bars) to the moment the bass drops out into the
 * breakdown at 76.75 s (sub-120 Hz falls ~45 dB in a quarter second).
 * The moon's column holds across this whole window.
 */
export const CLIMAX_START_MS = 63720;
export const CLIMAX_END_MS = 76750;

/** One explosion per hit inside the climax: the crash itself, then every
 * bar's snare. 68435 is filled in on the bar grid (midway between its
 * neighbours) — the detector skipped that bar as ambiguous. */
export const CLIMAX_BURST_MS: readonly number[] = [63720, 64691, 66560, 68435, 70310, 72191, 74060, 75929];

/** Length (ms) of the looped track, `assets/audio/creo-flow-loop.mp3`: the
 * song's first 1:33.5, cut in the near-silent gap after the fill at
 * 1:33.4 — just before the aggressive section's bass comes in at 1:33.7 —
 * so the loop goes quiet and the intro fades back in. The cut file is
 * sample-aligned with the full track (the MP3 encoder's 1105-sample
 * priming delay was trimmed from its head), so every time in this module
 * holds for it. Hits past the cut never come up. */
export const SONG_MS = 93500;

/** The glitch: every 33 s of song time, skipping any that would land in or
 * just before the climax (the one at 1:06 would cut across the column) —
 * which, on the 1:33.5 loop, leaves the one at 0:33 each time round. */
export const GLITCH_MS: readonly number[] = Array.from({ length: Math.floor(SONG_MS / 33000) }, (_, i) => (i + 1) * 33000).filter(
  (t) => t < CLIMAX_START_MS - 1000 || t > CLIMAX_END_MS,
);
