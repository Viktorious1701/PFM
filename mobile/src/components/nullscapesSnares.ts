/**
 * Snare-hit times (ms) in `assets/audio/creo-flow.mp3` (official version),
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
