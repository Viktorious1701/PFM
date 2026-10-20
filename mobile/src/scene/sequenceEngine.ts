// @ts-nocheck
/**
 * The Nullscapes background sequence — the approved draft (artifact
 * DvUm6dXpGtHfDAPR4v6X8p, v17) moved into the app unchanged, as a canvas
 * engine. Every scene, flash, glitch and transition is a pure function of
 * the track time, so the same `render(t)` serves playback, seeking, looping
 * and a paused frame.
 *
 * The drawing code is kept as the draft wrote it (plain JS, unchecked) so the
 * approved look can be compared line for line; only two things were added:
 * `CAM` / `SHEAR`, which carry the app's tab-pan camera into each layer's
 * horizontal offset (nearer layers move further) and the field's lean.
 *
 * Timeline (track ms): intro 0 · glitch 10.3 s · scene 1 (mountains) 12.1 s ·
 * scene 2 (storm) 41.8 s · glitch 57.5 s · scene 3 (moon) 59.5 s · climax
 * 74.46–87.49 s · outro 99.5 s · end 115.0 s. Creo Flow starts 10.742 s in,
 * so its measured snare and climax times are shifted by that much.
 */
export const TRACK_MS = 115000;

export type Sequence = {
  /** Draws the frame for track time `t` (ms). `cam` is the tab-pan camera in
   * scene units, `shear` the field's lean while panning. */
  render: (t: number, cam?: number, shear?: number) => void;
  /** Picks the full sequence, or the moon scene for the whole song. */
  setMode: (mode: SequenceMode) => void;
};

export type SequenceMode = 'full' | 'scene3';

/** Builds the engine on a 1280x720 canvas. */
export function createSequence(canvas: HTMLCanvasElement): Sequence {
  var ctx = canvas.getContext('2d');
  var W = 1280, H = 720;
  // camera from the app's tab pans (scene units; negative = moved forward)
  // and the lean of the field while it moves (tan of the angle)
  var CAM = 0, SHEAR = 0;

  // ---------- timeline (track ms) ----------
  var OFF = 10742; // Creo Flow 0:00 inside the new track
  var T = {
    introEnd: 9000, grey: 10300, g1End: 11800, black: 12100,
    s1Bright: 13300, drop: 14480, dropEnd: 15100, filterLift: 30000, dipA: 27600, dipB: 29000,
    duskA: 41800, duskB: 43300, stormA: 43300, stormIn: 44600, discA: 44600, discFull: 47800, stormB: 57300,
    glitchA: 57500, glitchB: 58750, black2: 59440, moonIn: 59500,
    breakA: 87500, outroA: 99500, outroB: 106000, end: 115000,
  };
  // which sequence plays: the full four scenes, or the moon scene for the whole song
  var MODE = 'full';
  var SNARES_ALL = [4679, 6560, 8429, 10310, 12190, 14060, 15929, 19691, 21560, 23429, 25310, 27191, 29060, 30929, 34691, 36560, 38429, 40310, 42191, 44060, 45929, 49691, 51560, 55310, 57191, 59095, 62810, 64691, 66560, 70310, 72191, 74060, 75929, 77810, 79679, 81560, 83429, 85310, 87191].map(function (s) { return s + OFF; });
  // ARRIVE: the white flash that brings the moon scene in (scene 3's first kick, or the drop's first drum)
  var ARRIVE, SNARES;
  function applyMode() {
    ARRIVE = MODE === 'scene3' ? T.drop : T.moonIn;
    // the dark beat (dipA..dipB) stays dark: no flashes there
    SNARES = SNARES_ALL.filter(function (s) { return s >= ARRIVE - 200 && s < T.outroA && !(s > T.dipA && s < T.dipB); });
  }
  applyMode();
  // scene 1's snares (after the drop, before dusk)
  var SN1 = [4679, 6560, 8429, 10310, 12190, 14060, 15929, 19691, 21560, 23429, 25310, 27191, 29060, 30929].map(function (x) { return x + OFF; }).filter(function (x) { return x > T.drop && x < T.duskA && (x < T.dipA || x > T.dipB); });
  var BEAT = 60000 / 129.2;
  // bar downbeats from the first kick of the drop (track 59.504 s) to the climax
  var BASS3 = []; for (var bt0 = 59504; bt0 < 63720 + OFF - 200; bt0 += 4 * BEAT) BASS3.push(bt0);
  var CLIMAX_A = 63720 + OFF, CLIMAX_B = 76750 + OFF;
  var BURSTS = [63720, 64691, 66560, 68435, 70310, 72191, 74060, 75929].map(function (s) { return s + OFF; });

  var SCENES = [
    { from: 0, to: T.grey, name: 'Intro', color: '#e8ecef' },
    { from: T.grey, to: T.black, name: 'Glitch', color: '#555b62' },
    { from: T.black, to: T.duskA, name: 'Scene 1 · mountains', color: '#b8c4c9' },
    { from: T.duskA, to: T.glitchA, name: 'Scene 2 · the storm', color: '#7f8a90' },
    { from: T.glitchA, to: T.moonIn, name: 'Glitch', color: '#555b62' },
    { from: T.moonIn, to: T.outroA, name: 'Scene 3 · moonlit', color: '#5f7da3' },
    { from: T.outroA, to: T.end, name: 'Outro', color: '#232a33' },
  ];

  // ---------- helpers ----------
  function mulberry32(seed) {
    var a = seed;
    return function () {
      a |= 0; a = (a + 0x6d2b79f5) | 0;
      var t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function clamp(x, a, b) { return Math.max(a, Math.min(b, x)); }
  function ramp(t, a, b) { return clamp((t - a) / (b - a), 0, 1); }
  function smooth(x) { return x * x * (3 - 2 * x); }
  function hash(n) { var r = mulberry32(n * 2654435761 >>> 0); r(); return r(); }
  function off(w, h) { var c = document.createElement('canvas'); c.width = w || W; c.height = h || H; return c; }

  // ---------- grass (the app's GRASS specs) ----------
  var MOON_CX = W * 0.49, MOON_CY = H * 0.5, MOON_R = H * 0.165;
  // scene 3's moon: lower, bigger, right of centre (the reference wallpaper)
  var M3X = W * 0.62, M3Y = H * 0.565, M3R = H * 0.215;
  var GRASS = [
    { seed: 5, baseY: H * 0.88, count: 220, minH: H * 0.12, maxH: H * 0.30, minW: 7, maxW: 18, leanDeg: 16 },
    { seed: 11, baseY: H * 0.98, count: 110, minH: H * 0.32, maxH: H * 0.52, minW: 14, maxW: 34, leanDeg: 18 },
    { seed: 47, baseY: H * 1.05, count: 46, minH: H * 0.48, maxH: H * 0.72, minW: 26, maxW: 64, leanDeg: 20, centerBoost: true },
  ];
  var BLADES = GRASS.map(function (o) {
    var rand = mulberry32(o.seed), spacing = W / o.count, out = [];
    for (var i = -1; i <= o.count + 1; i++) {
      var x = i * spacing + (rand() - 0.5) * spacing * 0.9;
      var boost = o.centerBoost ? Math.max(0, 1 - (Math.abs(x - MOON_CX) / (W * 0.5)) * 1.8) : 0;
      var h = o.minH + rand() * (o.maxH - o.minH) + boost * (o.maxH * 0.9) * rand();
      var w = o.minW + rand() * (o.maxW - o.minW);
      var lean = ((rand() - 0.5) * 2 * o.leanDeg) * Math.PI / 180;
      var side = rand() < 0.5 ? -1 : 1;
      out.push({ x: x, h: h, w: w, tipX: x + Math.sin(lean) * h, tipY: o.baseY - h * Math.cos(lean), side: side, baseY: o.baseY });
    }
    return out;
  });
  function drawGrass(g, fills, flash, shift) {
    BLADES.forEach(function (layer, li) {
      var dx = shift ? shift[li] : 0;
      layer.forEach(function (b) {
        g.beginPath();
        g.moveTo(b.x - b.w / 2 + dx, b.baseY); g.lineTo(b.tipX + dx, b.tipY); g.lineTo(b.x + b.w / 2 + dx, b.baseY); g.closePath();
        g.fillStyle = fills[li]; g.fill();
        if (flash > 0.01) {
          g.save(); g.globalCompositeOperation = 'lighter';
          g.strokeStyle = 'rgba(225,233,247,' + (flash * 0.5).toFixed(3) + ')';
          g.lineWidth = Math.max(1, b.w * 0.1);
          g.beginPath();
          g.moveTo(b.x + b.side * b.w * 0.18 + dx, b.baseY - b.h * 0.06);
          g.lineTo(b.tipX + b.side * b.w * 0.06 + dx, b.tipY + b.h * 0.08);
          g.stroke(); g.restore();
        }
      });
    });
  }
  var SPECKS = (function () {
    var r = mulberry32(777), out = [];
    for (var i = 0; i < 70; i++) out.push({ x: r() * W, y: r() * H, len: 4 + r() * 10, wid: 0.8 + r() * 1.4, rot: r() * 6.283, op: 0.15 + r() * 0.55 });
    return out;
  })();
  function drawSpecks(g, color) {
    SPECKS.forEach(function (p) {
      g.save(); g.translate(p.x, p.y); g.rotate(p.rot); g.globalAlpha = p.op; g.fillStyle = color;
      g.beginPath(); g.moveTo(0, -p.len / 2); g.lineTo(p.wid, 0); g.lineTo(0, p.len / 2); g.lineTo(-p.wid, 0); g.closePath(); g.fill();
      g.restore();
    });
  }

  // ---------- INTRO: the white meadow ----------
  var DUST = (function () {
    var r = mulberry32(31337), out = [];
    for (var i = 0; i < 110; i++) {
      var cluster = r() < 0.6;
      out.push({
        x: cluster ? (r() < 0.5 ? W * (0.04 + r() * 0.14) : W * (0.84 + r() * 0.14)) : r() * W,
        y: r() * H * 0.85, s: 2 + r() * 7, a: 0.18 + r() * 0.5, vx: 6 + r() * 14, vy: -3 - r() * 8, ph: r() * 6.28,
      });
    }
    return out;
  })();
  // Big translucent triangular spikes, leaning every way, two depths —
  // the intro level's own scenery (not our grass).
  var SPIKES = (function () {
    var r = mulberry32(4242), out = [];
    for (var i = 0; i < 70; i++) {
      var far = i < 30;
      var x = r() * (W + 200) - 100, h = H * (far ? 0.22 + r() * 0.28 : 0.3 + r() * 0.42);
      var w = far ? 26 + r() * 50 : 40 + r() * 90, lean = (r() - 0.5) * (far ? 0.9 : 1.4);
      out.push({ x: x, base: H * (far ? 0.86 : 1.02), h: h, w: w, lean: lean, a: far ? 0.22 + r() * 0.16 : 0.34 + r() * 0.34, far: far, l: r() });
    }
    return out.sort(function (a, b) { return (b.far ? 1 : 0) - (a.far ? 1 : 0); });
  })();
  function drawIntro(t) {
    var g = ctx, s = t / 1000;
    // the world greys as the intro goes on (0:08–0:10 frames are darker)
    var age = smooth(ramp(t, 4000, T.grey));
    var bgL = Math.round(246 - age * 10);
    g.fillStyle = 'rgb(' + bgL + ',' + (bgL + 1) + ',' + (bgL + 3) + ')'; g.fillRect(0, 0, W, H);
    SPIKES.forEach(function (sp, i) {
      var drift = sp.far ? 7 : 18;
      var x = ((sp.x - s * drift + CAM * (sp.far ? 0.35 : 0.8)) % (W + 200) + W + 200) % (W + 200) - 100;
      var tipX = x + sp.lean * sp.h, tipY = sp.base - sp.h;
      var shade = Math.round((sp.far ? 140 : 80) - age * 25 + sp.l * 30);
      var grd = g.createLinearGradient(0, tipY, 0, sp.base);
      grd.addColorStop(0, 'rgba(' + shade + ',' + shade + ',' + (shade + 3) + ',' + (sp.a * (0.55 + age * 0.5)).toFixed(3) + ')');
      grd.addColorStop(1, 'rgba(' + shade + ',' + shade + ',' + (shade + 3) + ',' + (sp.a * 0.25).toFixed(3) + ')');
      g.fillStyle = grd;
      g.beginPath(); g.moveTo(x - sp.w / 2, sp.base); g.lineTo(tipX, tipY); g.lineTo(x + sp.w / 2, sp.base); g.closePath(); g.fill();
      // one lit face, like the faceted spikes in the reference
      g.fillStyle = 'rgba(255,255,255,' + (sp.a * 0.35).toFixed(3) + ')';
      g.beginPath(); g.moveTo(x, sp.base); g.lineTo(tipX, tipY); g.lineTo(x + sp.w / 2, sp.base); g.closePath(); g.fill();
    });
    // ground fog
    var fog = g.createLinearGradient(0, H * 0.5, 0, H);
    fog.addColorStop(0, 'rgba(246,247,249,0)'); fog.addColorStop(0.6, 'rgba(246,247,249,0.6)'); fog.addColorStop(1, 'rgba(248,249,250,0.95)');
    g.fillStyle = fog; g.fillRect(0, 0, W, H);
    for (var k = 0; k < 5; k++) {
      var fx = ((s * (10 + k * 6) + k * 330) % (W + 600)) - 300, fy = H * (0.62 + k * 0.07);
      var fb = g.createRadialGradient(fx, fy, 0, fx, fy, 260);
      fb.addColorStop(0, 'rgba(250,251,252,0.5)'); fb.addColorStop(1, 'rgba(250,251,252,0)');
      g.fillStyle = fb; g.fillRect(0, 0, W, H);
    }
    // floating dust squares, thicker in drifting columns at the edges
    DUST.forEach(function (d) {
      var x = ((d.x + d.vx * s + CAM) % (W + 40) + W + 40) % (W + 40) - 20;
      var y = ((d.y + d.vy * s) % H + H) % H;
      g.globalAlpha = d.a * (0.6 + 0.4 * Math.sin(s * 1.3 + d.ph)) * (0.6 + age * 0.6);
      g.fillStyle = '#7d838a'; g.fillRect(x, y, d.s, d.s);
    });
    g.globalAlpha = 1;
    // fade up from black at the loop start; dim to grey before the cut
    var dim = smooth(ramp(t, T.introEnd, T.grey));
    if (dim > 0) { g.fillStyle = 'rgba(130,130,130,' + (dim * 0.62).toFixed(3) + ')'; g.fillRect(0, 0, W, H); }
    var rise = 1 - smooth(ramp(t, 0, 1500));
    if (rise > 0) { g.fillStyle = 'rgba(0,0,0,' + rise.toFixed(3) + ')'; g.fillRect(0, 0, W, H); }
  }

  // ---------- SCENES 1–2: low-poly mountains ----------
  // A ridge is a strip of flat-shaded triangles between its jagged top edge
  // and the bottom of the frame; vertices get a fake depth so each facet
  // catches a slightly different light, like the reference.
  function buildRidge(seed, o) {
    var r = mulberry32(seed), n = o.points, step = W / n, top = [], mid = [];
    var peaks = o.peaks.map(function (p) { return { x: p[0] * W, h: p[1] * H, w: p[2] * W }; });
    for (var i = 0; i <= n; i++) {
      var x = i * step + (i === 0 || i === n ? 0 : (r() - 0.5) * step * 0.5);
      var hgt = o.amp * (0.35 + 0.65 * r());
      peaks.forEach(function (p) {
        // peaks also wrap, so the tiled ridge has no seam
        var d = Math.min(Math.abs(x - p.x), Math.abs(x - p.x - W), Math.abs(x - p.x + W));
        hgt += p.h * Math.max(0, 1 - d / p.w);
      });
      top.push({ x: x, y: o.baseY - hgt, z: r() });
      mid.push({ x: x + (r() - 0.5) * step * 0.6, y: o.baseY + (H - o.baseY) * (0.35 + r() * 0.3) - hgt * 0.35, z: r() });
    }
    top[n].y = top[0].y; top[n].z = top[0].z; mid[n].y = mid[0].y; mid[n].x = W + (mid[0].x);
    var tris = [];
    for (var j = 0; j < n; j++) {
      var a = top[j], b = top[j + 1], c = mid[j], d = mid[j + 1];
      var e = { x: c.x, y: H + 40, z: 0.5 }, f = { x: d.x, y: H + 40, z: 0.5 };
      [[a, b, c], [b, d, c], [c, d, e], [d, f, e]].forEach(function (t) { tris.push(shade(t, o, r)); });
    }
    return tris;
  }
  function shade(t, o, r) {
    // normal of the triangle with pseudo-depth -> lambert against an upper-left light
    var p = t.map(function (v) { return [v.x, v.y, v.z * 260]; });
    var ux = p[1][0] - p[0][0], uy = p[1][1] - p[0][1], uz = p[1][2] - p[0][2];
    var vx = p[2][0] - p[0][0], vy = p[2][1] - p[0][1], vz = p[2][2] - p[0][2];
    var nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;
    var len = Math.hypot(nx, ny, nz) || 1; nx /= len; ny /= len; nz /= len;
    if (nz < 0) { nx = -nx; ny = -ny; nz = -nz; }
    var lit = clamp(0.55 + 0.45 * (-0.55 * nx - 0.45 * ny + 0.7 * nz), 0, 1);
    var l = o.light + (lit - 0.6) * o.contrast + (r() - 0.5) * o.jitter;
    return { pts: t.map(function (v) { return [v.x, v.y]; }), l: clamp(l, 0, 1) };
  }
  var RIDGES = [
    { tris: buildRidge(101, { points: 14, baseY: H * 0.60, amp: H * 0.07, peaks: [[0.2, 0.08, 0.2], [0.78, 0.26, 0.15]], light: 0.86, contrast: 0.18, jitter: 0.03 }), speed: 4, tint: [204, 214, 218] },
    { tris: buildRidge(202, { points: 16, baseY: H * 0.66, amp: H * 0.06, peaks: [[0.3, 0.08, 0.18], [0.6, 0.2, 0.1]], light: 0.52, contrast: 0.34, jitter: 0.05 }), speed: 11, tint: [146, 152, 156] },
    { tris: buildRidge(303, { points: 22, baseY: H * 0.72, amp: H * 0.03, peaks: [[0.15, 0.03, 0.1], [0.62, 0.04, 0.12]], light: 0.0, contrast: 0.12, jitter: 0.03 }), speed: 22, tint: [22, 23, 25] },
  ];
  function drawRidge(g, R, dx, night) {
    for (var k = -1; k <= 1; k++) {
      R.tris.forEach(function (tr) {
        var c = R.tint.map(function (ch) { return Math.round(ch * (0.35 + 0.95 * tr.l) * (1 - night * 0.8)); });
        g.fillStyle = 'rgb(' + c.join(',') + ')';
        g.beginPath();
        g.moveTo(tr.pts[0][0] + dx + k * W, tr.pts[0][1]);
        g.lineTo(tr.pts[1][0] + dx + k * W, tr.pts[1][1]);
        g.lineTo(tr.pts[2][0] + dx + k * W, tr.pts[2][1]);
        g.closePath(); g.fill();
        g.strokeStyle = g.fillStyle; g.lineWidth = 0.8; g.stroke(); // hide hairline seams
      });
    }
  }
  var mtnBuf = off(), mtnCtx = mtnBuf.getContext('2d');
  var relocate = 0;
  function drawMountainsTo(g, t, night) {
    var s = t / 1000;
    var sky = g.createLinearGradient(0, 0, 0, H * 0.8);
    var n = night;
    function mix(a, b) { return Math.round(a + (b - a) * n); }
    sky.addColorStop(0, 'rgb(' + mix(214, 34) + ',' + mix(226, 37) + ',' + mix(230, 40) + ')');
    sky.addColorStop(1, 'rgb(' + mix(236, 44) + ',' + mix(242, 47) + ',' + mix(243, 50) + ')');
    g.fillStyle = sky; g.fillRect(0, 0, W, H);
    RIDGES.forEach(function (R, i) {
      drawRidge(g, R, -(((s * R.speed) + relocate - CAM * R.speed / 22) % W), n);
      if (i < 2) {
        // mist pooling at the foot of each ridge
        var y0 = i === 0 ? H * 0.52 : H * 0.62;
        var m = g.createLinearGradient(0, y0 - 40, 0, y0 + 70);
        var a = (1 - n) * 0.32 + n * 0.04;
        m.addColorStop(0, 'rgba(232,238,240,0)'); m.addColorStop(0.55, 'rgba(232,238,240,' + a.toFixed(3) + ')'); m.addColorStop(1, 'rgba(232,238,240,0)');
        g.fillStyle = m; g.fillRect(0, y0 - 40, W, 110);
      }
    });
  }
  function drawMountains(t) {
    if (t >= T.stormA) { drawStorm(t); return; }
    // brightness: rises out of black at the scene start, a short dip at
    // 0:28 (the filter lifting), night falls at 0:42 — which also covers
    // the cut to scene 2's lower, wider view
    var night = 1 - smooth(ramp(t, T.black, T.s1Bright));
    // the dark beat at 0:27.6: the scene drops to near-dark and, unseen in
    // the dark, the camera jumps — it comes back on a new stretch of range
    var dip = t > T.dipA && t < T.dipB ? Math.min(1, Math.sin(Math.PI * (t - T.dipA) / (T.dipB - T.dipA)) * 1.6) : 0;
    // the cut into scene 2 is the same kind of dark stutter, not a fade
    var cut2 = t >= T.duskA && t < T.stormA ? Math.min(1, (t - T.duskA) / 120) : 0;
    night = Math.max(night, dip, cut2 * 0.9);
    var stutterStart = t >= T.dipA && t < T.dipB ? T.dipA + 120 : cut2 > 0 ? T.duskA + 120 : -1;
    var stutter = stutterStart >= 0 && t >= stutterStart;
    var muffle = 1 - ramp(t, 24000, T.filterLift);
    // Scene 1 opens zoomed right in on one mountain face, creeping slowly,
    // and pulls out to the full range on the first drum hit (track 0:14.48).
    // Drawn straight to the canvas under a transform so the facets stay crisp.
    var out = t < T.drop ? 0 : 1 - Math.pow(1 - ramp(t, T.drop, T.dropEnd), 3);
    var zin = 2.5 + 0.2 * ramp(t, T.black, T.drop);
    var z = zin + (1 - zin) * out;
    var fx = W * 0.33, fy = H * 0.58;
    var cx = fx + (W / 2 - fx) * out, cy = fy + (H / 2 - fy) * out;
    ctx.save();
    ctx.translate(W / 2, H / 2); ctx.scale(z, z); ctx.translate(-cx, -cy);
    var moved = t >= (T.dipA + T.dipB) / 2 && t < T.duskA;
    relocate = moved ? W * 0.37 : 0;
    if (stutter) {
      // while it's dark the camera jumps between positions every ~110 ms:
      // sideways along the range, horizon up or down, a little zoom
      // changes at 0, 0.3, 0.6 s, a pause, then two more at 1.15 and 1.45 s
      var CH = [0, 300, 600, 1150, 1450], idx = 0;
      for (var ci = 0; ci < CH.length; ci++) if (t - stutterStart >= CH[ci]) idx = ci;
      var k = Math.floor(stutterStart / 7) + idx * 13;
      var zz = 1.08 + hash(k * 5 + 1) * 0.16;
      ctx.translate(W / 2, H / 2); ctx.scale(zz, zz);
      ctx.translate(-W / 2, -H / 2 + (hash(k * 5 + 2) - 0.5) * H * 0.09);
      relocate = hash(k * 5 + 3) * W;
    }
    drawMountainsTo(ctx, t, night);
    relocate = 0;
    ctx.restore();
    // snare flashes, alternating: a slight dim, then a soft pale lift —
    // subtle enough that the scene reads the same, just noticeably pulsing
    var f = 0, kind = 0;
    for (var i = 0; i < SN1.length; i++) {
      var e = envelope(t - (SN1[i] - 60), 60, 70, 600);
      if (e > f) { f = e; kind = i % 2; }
    }
    if (f > 0.01 && night < 0.5) {
      if (kind === 0) { ctx.fillStyle = 'rgba(20,24,28,' + (f * 0.09).toFixed(3) + ')'; ctx.fillRect(0, 0, W, H); }
      else {
        var lift = ctx.createLinearGradient(0, H * 0.5, 0, H);
        lift.addColorStop(0, 'rgba(225,232,236,' + (f * 0.06).toFixed(3) + ')'); lift.addColorStop(1, 'rgba(160,168,172,' + (f * 0.32).toFixed(3) + ')');
        ctx.fillStyle = lift; ctx.fillRect(0, 0, W, H);
      }
    }
  }

  // ---------- SCENE 2: the storm coming ----------
  // Low mountains under a mottled cloud sky. A half-disc of concentric
  // bands rises behind them, growing and darkening toward a black core,
  // while the sky greys and black leaf-shards blow across in growing
  // numbers — then it all smears into the glitch.
  var STORM_RIDGES = [
    { tris: buildRidge(511, { points: 13, baseY: H * 0.72, amp: H * 0.006, peaks: [[0.1, 0.19, 0.11], [0.44, 0.05, 0.18], [0.83, 0.1, 0.13]], light: 0.86, contrast: 0.2, jitter: 0.05 }), speed: 6, tint: [212, 214, 216] },
    { tris: buildRidge(622, { points: 15, baseY: H * 0.79, amp: H * 0.006, peaks: [[0.33, 0.22, 0.08], [0.58, 0.07, 0.1], [0.97, 0.15, 0.07]], light: 0.55, contrast: 0.36, jitter: 0.06 }), speed: 13, tint: [150, 152, 155] },
    { tris: buildRidge(733, { points: 17, baseY: H * 0.85, amp: H * 0.008, peaks: [[0.05, 0.16, 0.07], [0.4, 0.08, 0.09], [0.7, 0.04, 0.06]], light: 0.14, contrast: 0.3, jitter: 0.05 }), speed: 24, tint: [44, 44, 47] },
  ];
  // the cloud texture: soft grey blobs, drawn small and scaled up (smooth)
  var CLOUDS = (function () {
    var c = off(320, 180), g = c.getContext('2d'), r = mulberry32(2626);
    g.fillStyle = '#fff'; g.fillRect(0, 0, 320, 180);
    for (var i = 0; i < 70; i++) {
      var x = r() * 320, y = r() * 180, rad = 14 + r() * 30, a = 0.05 + r() * 0.12;
      for (var k = -1; k <= 1; k++) {
        var gr = g.createRadialGradient(x + k * 320, y, 0, x + k * 320, y, rad);
        gr.addColorStop(0, 'rgba(0,0,0,' + a.toFixed(3) + ')'); gr.addColorStop(1, 'rgba(0,0,0,0)');
        g.fillStyle = gr; g.fillRect(0, 0, 320, 180);
      }
    }
    return c;
  })();
  var LEAVES = (function () {
    var r = mulberry32(8080), out = [];
    for (var i = 0; i < 130; i++) out.push({ x: r() * (W + 80), y: r() * H * 0.95, sp: 0.6 + r() * 0.8, fall: 4 + r() * 10, flut: 6 + r() * 14, ph: r() * 6.28, rot: r() * 6.28, spin: (r() - 0.5) * 5, size: r(), grey: r() < 0.35 });
    return out;
  })();
  function stormLevel(t) { return clamp((t - T.stormA) / (T.stormB - T.stormA), 0, 1); }
  // distance the wind has carried things: integral of (base + gust * level)
  function windDist(t) {
    var a = T.stormA, b = T.stormB, base = 30, gust = 230, s = (t - a) / 1000, span = (b - a) / 1000;
    var integ = t < a ? 0 : t < b ? 0.5 * s * s / span : span / 2 + (s - span);
    return base * (t / 1000) + gust * integ;
  }
  function drawStorm(t) {
    var g = ctx, lvl = stormLevel(t), s = t / 1000;
    // the sky greys as the storm builds
    var skyL = Math.round(232 - 40 * smooth(lvl));
    g.fillStyle = 'rgb(' + skyL + ',' + (skyL + 4) + ',' + (skyL + 6) + ')'; g.fillRect(0, 0, W, H);
    g.save(); g.globalAlpha = 0.55 + 0.3 * lvl; g.globalCompositeOperation = 'multiply';
    var cx = -(((windDist(t) * 0.05) - CAM * 0.05) % W);
    g.drawImage(CLOUDS, cx, 0, W, H); g.drawImage(CLOUDS, cx + W, 0, W, H);
    g.restore();

    // the banded half-disc, rising and darkening behind the mountains
    var appear = smooth(ramp(t, T.discA, T.discA + 900));
    if (appear > 0) {
      var grow = smooth(ramp(t, T.discA, T.discFull));
      var dark = smooth(ramp(t, T.discA + 600, T.stormB));
      var DX = W * 0.62, DY = H * 0.60, R = W * (0.15 + 0.11 * grow);
      g.save();
      g.beginPath(); g.rect(0, 0, W, DY); g.clip();
      // stepped bands at the rim
      var BANDS = 9;
      for (var b = 0; b < BANDS; b++) {
        var u = b / BANDS;                       // 0 outermost
        var L = skyL - (skyL - 150) * u * (0.4 + 0.6 * dark) - 8;
        var al = appear * (0.3 + 0.55 * u);
        g.fillStyle = 'rgba(' + Math.round(L) + ',' + Math.round(L) + ',' + Math.round(L + 2) + ',' + al.toFixed(3) + ')';
        g.beginPath(); g.arc(DX, DY, R * (1 - u * 0.32), Math.PI, 0); g.fill();
      }
      // a smooth dark core inside, deepening with the storm
      var hx = DX + Math.sin(s * 0.7) * R * 0.04;
      var hg = g.createRadialGradient(hx, DY + R * 0.05, 0, hx, DY, R * 0.7);
      var core = Math.round(150 - 125 * dark);
      hg.addColorStop(0, 'rgba(' + core + ',' + core + ',' + (core + 2) + ',' + appear.toFixed(3) + ')');
      hg.addColorStop(0.75, 'rgba(' + (core + 40) + ',' + (core + 40) + ',' + (core + 42) + ',' + (appear * 0.85).toFixed(3) + ')');
      hg.addColorStop(1, 'rgba(160,160,162,' + (appear * 0.6).toFixed(3) + ')');
      g.fillStyle = hg; g.beginPath(); g.arc(DX, DY, R * 0.68, Math.PI, 0); g.fill();
      g.restore();
    }
    // a pale mist bank cutting the disc's base, slightly tilted
    var mistY = H * 0.6;
    var mg = g.createLinearGradient(0, mistY - 6, 0, H * 0.78);
    var mL = skyL + 6;
    mg.addColorStop(0, 'rgba(' + mL + ',' + mL + ',' + (mL + 2) + ',0.92)'); mg.addColorStop(1, 'rgba(' + mL + ',' + mL + ',' + (mL + 2) + ',0.4)');
    g.fillStyle = mg;
    g.globalAlpha = 0.8;
    g.beginPath(); g.moveTo(W * 0.32, mistY + 30); g.lineTo(W * 0.4, mistY + 2); g.lineTo(W * 0.62, mistY - 3); g.lineTo(W * 0.85, mistY - 12); g.lineTo(W, mistY - 4); g.lineTo(W, H * 0.74); g.lineTo(W * 0.3, H * 0.74); g.closePath(); g.fill();
    g.globalAlpha = 1;

    // the mountains, low, greying with the sky
    STORM_RIDGES.forEach(function (Rg) { drawRidge(g, Rg, -((s * Rg.speed - CAM * Rg.speed / 24 + windDist(t) * Rg.speed * 0.004) % W), lvl * 0.25); });
    var fog = g.createLinearGradient(0, H * 0.7, 0, H * 0.8);
    fog.addColorStop(0, 'rgba(200,202,205,0)'); fog.addColorStop(0.5, 'rgba(200,202,205,' + (0.22 - lvl * 0.1).toFixed(3) + ')'); fog.addColorStop(1, 'rgba(200,202,205,0)');
    g.fillStyle = fog; g.fillRect(0, H * 0.7, W, H * 0.1);
    var bottom = g.createLinearGradient(0, H * 0.82, 0, H);
    bottom.addColorStop(0, 'rgba(6,6,7,0)'); bottom.addColorStop(1, 'rgba(6,6,7,0.95)');
    g.fillStyle = bottom; g.fillRect(0, H * 0.82, W, H * 0.18);

    // leaves: a few specks when calm, a gale of black shards at the end
    var count = Math.round(14 + 50 * Math.pow(lvl, 0.8));
    var wd = windDist(t);
    for (var i = 0; i < count; i++) {
      var lf = LEAVES[i];
      var x = ((lf.x + wd * lf.sp + CAM) % (W + 80) + W + 80) % (W + 80) - 40;
      var y = ((lf.y + s * lf.fall * (1 + lvl) + Math.sin(s * 2 + lf.ph) * lf.flut) % H + H) % H;
      var size = lf.grey ? 1.2 + lf.size * 1.6 : (2 + lf.size * 2.5) * (1 + 0.7 * lvl);
      g.save(); g.translate(x, y); g.rotate(lf.rot + s * lf.spin);
      g.fillStyle = lf.grey ? 'rgba(110,110,112,0.7)' : 'rgba(22,22,24,0.95)';
      g.beginPath(); g.moveTo(size, 0); g.lineTo(-size * 0.8, size * 0.55); g.lineTo(-size * 0.4, -size * 0.6); g.closePath(); g.fill();
      g.restore();
    }
    // out of the dusk dip into the storm view
    var cover = 0;
    if (cover > 0) { g.fillStyle = 'rgba(30,32,34,' + cover.toFixed(3) + ')'; g.fillRect(0, 0, W, H); }
  }

  // ---------- GLITCH 2: the streak smear + the line ----------
  var smearBuf = off(), smearCtx = smearBuf.getContext('2d');
  var greyBuf = off(), greyCtx = greyBuf.getContext('2d');
  var greyFor = -1;
  var tinyBuf = off(96, 54), tinyCtx = tinyBuf.getContext('2d');
  // since: ms into the glitch; dur: its length; drawSource(): the frame
  // being smeared; words: whether the line appears; wave: how much the
  // streaks bend (they straighten out as wave falls to 0).
  function drawGlitch(t, since, dur, drawSource, srcKey, words, wave, tone, fullFrame) {
    if (greyFor !== srcKey) {
      drawSource();
      greyCtx.filter = 'grayscale(1) contrast(1.2) brightness(' + tone + ')';
      if (fullFrame) {
        // soften first, so it smears into a smudge rather than hard bands
        tinyCtx.drawImage(canvas, 0, 0, 96, 54);
        greyCtx.imageSmoothingQuality = 'high'; greyCtx.drawImage(tinyBuf, 0, 0, W, H);
      } else greyCtx.drawImage(canvas, 0, 0);
      greyCtx.filter = 'none';
      greyFor = srcKey;
    }
    var on = 1;
    if (since < 320) on = Math.floor(since / 55) % 2 === 0 ? 1 : (since < 160 ? 0 : 0.5);
    if (since > dur - 220) on = Math.floor((dur - since) / 50) % 2 === 0 ? 1 : 0;
    ctx.fillStyle = tone < 0.6 ? '#3e3e3e' : '#a2a2a2'; ctx.fillRect(0, 0, W, H);
    if (fullFrame) {
      // each row keeps its own content, rippled sideways, then smeared
      // horizontally — the storm dissolving rather than torn into bands
      smearCtx.clearRect(0, 0, W, H);
      var amp = 18 + 50 * smooth(ramp(since, 0, 900));
      for (var ry = 0; ry < H; ry += 3) {
        var rip = Math.sin(ry * 0.09 + t * 0.012) * amp + Math.sin(ry * 0.023 - t * 0.004) * amp * 0.6;
        smearCtx.drawImage(greyBuf, 0, ry, W, 3, rip, ry, W, 3);
        smearCtx.drawImage(greyBuf, 0, ry, 2, 3, rip - W, ry, W, 3); // fill the edge
      }
      var passes = 7, reach = 40 + 160 * smooth(ramp(since, 200, 1400));
      ctx.globalAlpha = on;
      ctx.drawImage(smearBuf, 0, 0);
      for (var k = 1; k <= passes; k++) {
        ctx.globalAlpha = on / (k + 1);
        ctx.drawImage(smearBuf, k * reach / passes, 0); ctx.drawImage(smearBuf, -k * reach / passes, 0);
      }
      // lift toward the flat grey it ends on
      ctx.globalAlpha = 1;
      ctx.fillStyle = 'rgba(165,165,165,' + (0.25 + 0.45 * smooth(ramp(since, 600, dur))).toFixed(3) + ')'; ctx.fillRect(0, 0, W, H);
      var tick = Math.floor(t / 60);
      for (var yy = 0; yy < H; yy += 2) {
        var n = hash(yy * 131 + tick * 7);
        if (n < 0.6) continue;
        ctx.fillStyle = 'rgba(120,120,120,' + ((n - 0.6) * 0.3 * on).toFixed(3) + ')';
        ctx.fillRect(hash(yy * 17 + tick) * W * 0.5, yy, W * (0.2 + hash(yy + tick * 3) * 0.5), 1);
      }
      return;
    }
    smearCtx.clearRect(0, 0, W, H);
    var BEND = wave, LEN = 0.2;
    for (var y = 0; y < H; y += 3) {
      var phase = y * 0.011 + t * 0.0011;
      var sw = 10 + (1 - LEN) * 260 + 24 * (0.5 + 0.5 * Math.sin(y * 0.05 + t * 0.0009));
      var sx = clamp(W * 0.5 + Math.sin(phase) * W * 0.32 * BEND + Math.sin(y * 0.037 - t * 0.0017) * W * 0.06 * BEND, 0, W - sw);
      var sy = clamp((fullFrame ? y * 0.9 + H * 0.02 : H * 0.24 + y * 0.42) + Math.sin(y * 0.02 + t * 0.0013) * 34 * BEND, 0, H - 3);
      var dx = -W * 0.35 + Math.sin(phase * 0.8 + 1.3) * W * 0.25 * BEND;
      smearCtx.drawImage(greyBuf, sx, sy, sw, 3, dx, y, W * 1.7, 3);
    }
    ctx.globalAlpha = on; ctx.drawImage(smearBuf, 0, 0); ctx.globalAlpha = 1;
    if (!words) {
      // fine horizontal grain: the second glitch tears into thin streaks
      var tick = Math.floor(t / 60);
      for (var yy = 0; yy < H; yy += 2) {
        var n = hash(yy * 131 + tick * 7);
        if (n < 0.5) continue;
        ctx.fillStyle = (n > 0.8 ? 'rgba(235,235,235,' : 'rgba(60,60,60,') + ((n - 0.5) * 0.35 * on).toFixed(3) + ')';
        var x0 = hash(yy * 17 + tick) * W * 0.6;
        ctx.fillRect(x0, yy, W * (0.3 + hash(yy + tick * 3) * 0.7), 1 + (n > 0.9 ? 1 : 0));
      }
      return;
    }
    var wIn = 300, wOut = dur - 250;
    var a = since < wIn ? 0 : since < wIn + 350 ? (since - wIn) / 350 : since < wOut - 250 ? 1 : since < wOut ? (wOut - since) / 250 : 0;
    if (a > 0.01) {
      var shiver = on < 1 ? (hash(Math.floor(t / 40)) - 0.5) * 10 : 0;
      ctx.save();
      ctx.font = '64px "CormorantGaramond_300Light", "Cormorant Garamond", Georgia, serif'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      if ('letterSpacing' in ctx) ctx.letterSpacing = '6px';
      ctx.fillStyle = 'rgba(205,205,205,' + (a * 0.22).toFixed(3) + ')';
      ctx.fillText('get out of my head', W / 2 - 4 + shiver, H / 2 + 12); ctx.fillText('get out of my head', W / 2 + 3 + shiver, H / 2 + 9);
      ctx.fillStyle = 'rgba(165,165,165,' + (a * 0.85).toFixed(3) + ')';
      ctx.fillText('get out of my head', W / 2 + shiver, H / 2 + 10);
      ctx.restore();
    }
  }

  // ---------- SCENE 3: the moonlit grass, flash, climax ----------
  function envelope(dt, ramp_, hold, fade) {
    if (dt < 0) return 0;
    if (dt < ramp_) return 1 - Math.pow(1 - dt / ramp_, 2);
    if (dt < ramp_ + hold) return 1;
    var u = (dt - ramp_ - hold) / fade; return u >= 1 ? 0 : 1 - u * u;
  }
  function flashAt(t) {
    // same envelope as the app: 60 ms ramp (peaks on the hit), 70 ms hold, 600 ms fade
    var best = 0;
    for (var i = 0; i < SNARES.length; i++) {
      var dt = t - (SNARES[i] - 60);
      if (dt < -10) break;
      if (dt < 800) best = Math.max(best, envelope(dt, 60, 70, 600));
    }
    for (var j = 0; j < BURSTS.length; j++) best = Math.max(best, envelope(t - (BURSTS[j] - 60), 60, 70, 600));
    return best;
  }
  var COLUMN_STEPS = 22, COLUMN_TOP = -60, COLUMN_BOTTOM = M3Y - M3R * 0.3;
  function sway(t) {
    // every 60–180 ms the top picks a new lean (usually the other side) and
    // bend, and snaps there in ~35 ms; deterministic in track time
    var since = t - CLIMAX_A, k = 0, at = 0, prevLean = 0, prevBend = 0.5, lean = 0, bend = 0.5, side = 1;
    while (true) {
      var len = 60 + hash(k * 7 + 1) * 120;
      side = hash(k * 7 + 2) < 0.75 ? -side : side;
      var targetLean = side * M3R * (0.25 + hash(k * 7 + 3) * 0.6), targetBend = hash(k * 7 + 4);
      if (since < at + len) {
        var p = 1 - Math.exp(-(since - at) / 35);
        lean = prevLean + (targetLean - prevLean) * p; bend = prevBend + (targetBend - prevBend) * p;
        break;
      }
      prevLean = targetLean; prevBend = targetBend; at += len; k++;
      if (k > 400) break;
    }
    return { lean: lean + (hash(Math.floor(t / 16)) - 0.5) * M3R * 0.03, bend: bend };
  }

  var ORB_SEEDS = BURSTS.map(function (_, i) {
    var r = mulberry32(900 + i), orbs = [], glows = [];
    for (var n = 0; n < 45; n++) { var a = -Math.PI / 2 + (r() - 0.5) * Math.PI * 1.5; orbs.push({ a: a, sp: 560 * (0.55 + r() * 0.9), d: r() * 0.45, s: 3 * (0.6 + r() * 0.9), al: 0.7 + r() * 0.3 }); }
    for (var m = 0; m < 6; m++) { var b = -Math.PI / 2 + (r() - 0.5) * Math.PI * 1.7; glows.push({ a: b, sp: 560 * (0.3 + r() * 0.35), d: r() * 0.3, rad: 34 + r() * 44, al: 0.24 + r() * 0.16 }); }
    return { orbs: orbs, glows: glows };
  });

  // ---- the spike field: dense, big, leaning right with the wind ----
  var FIELD = [
    { n: 70, base: 0.66, hMin: 0.14, hMax: 0.30, wMin: 26, wMax: 60, lean: 0.55, col: [44, 60, 88], seed: 301 },
    { n: 55, base: 0.80, hMin: 0.22, hMax: 0.42, wMin: 40, wMax: 90, lean: 0.62, col: [32, 46, 72], seed: 302 },
    { n: 40, base: 0.96, hMin: 0.30, hMax: 0.55, wMin: 60, wMax: 130, lean: 0.70, col: [23, 35, 57], seed: 303 },
    { n: 26, base: 1.10, hMin: 0.36, hMax: 0.62, wMin: 90, wMax: 190, lean: 0.75, col: [16, 26, 44], seed: 304 },
  ].map(function (L) {
    var r = mulberry32(L.seed), out = [];
    for (var i = 0; i < L.n; i++) {
      out.push({ x: (i + r() * 0.9) * (W + 300) / L.n - 150, h: H * (L.hMin + r() * (L.hMax - L.hMin)), w: L.wMin + r() * (L.wMax - L.wMin), lean: L.lean * (0.6 + r() * 0.7), side: r(), ph: r() * 6.28, sh: r() });
    }
    return { blades: out, base: H * L.base, col: L.col };
  });
  // d3: how "3D" the spikes read, 0..1. At 0 each spike is a flat
  // silhouette; on a flash it becomes a faceted solid — a lit face toward
  // the moon and a shadow face, split down a ridge, brightening toward the
  // tip, with a soft highlight catching the ridge and the lit edge.
  var TRAVEL = [88, 160, 280, 460];   // px/s, far → near
  function drawField(g, t, gust, lit, d3) {
    var s = t / 1000;
    d3 = d3 || 0;
    FIELD.forEach(function (L, li) {
      var depth = 0.55 + 0.45 * li / 3;            // nearer layers shade harder
      // one gradient pair per layer (not per spike): from the layer's base up
      // to its tallest tips; per-spike strength goes through globalAlpha
      var topY = L.base - H * 0.62, lg = null, hg = null;
      if (d3 >= 0.02) {
        lg = g.createLinearGradient(0, L.base, 0, topY);
        lg.addColorStop(0, 'rgba(150,166,190,0.1)'); lg.addColorStop(1, 'rgba(196,210,230,1)');
        hg = g.createLinearGradient(0, L.base, 0, topY);
        hg.addColorStop(0, 'rgba(214,226,242,0)'); hg.addColorStop(1, 'rgba(214,226,242,1)');
      }
      // facet geometry is collected per layer and drawn in three batched
      // passes after the spikes (lit faces, shadow faces, edge highlights)
      var faces = d3 >= 0.02 ? [] : null;
      var span = W + 300, travel = s * TRAVEL[li] - CAM * TRAVEL[li] / TRAVEL[3];
      L.blades.forEach(function (b0) {
        // the field travels right to left past the viewer, nearer layers faster
        var b = { x: ((b0.x + 150 - travel) % span + span) % span - 150, h: b0.h, w: b0.w, lean: b0.lean, side: b0.side, ph: b0.ph, sh: b0.sh };
        var wave = Math.sin(s * (1.1 + li * 0.15) + b.ph + b0.x * 0.004) * (0.06 + 0.14 * gust);
        var lean = b.lean + wave + gust * 0.12 + SHEAR * (0.4 + 0.6 * li / 3);
        var tipX = b.x + Math.tan(Math.min(1.25, lean)) * b.h * 0.55, tipY = L.base - b.h;
        var k = 0.8 + b.sh * 0.35;
        var c = L.col.map(function (v, ci) { return Math.round(v * k + lit * (ci === 2 ? 90 : 70) * (1 - 0.6 * li / 3)); });
        var lx = b.x - b.w / 2, rx = b.x + b.w / 2;
        // the ridge: where the two faces meet, part-way across the base
        var mx = b.x + (b.side - 0.5) * b.w * 0.5;
        g.fillStyle = 'rgb(' + c.join(',') + ')';
        g.beginPath(); g.moveTo(lx, L.base); g.lineTo(tipX, tipY); g.lineTo(rx, L.base); g.closePath(); g.fill();
        // at rest: the faint flat lit face it always had
        var lf = 0.012 + 0.035 * b.side + lit * 0.3;
        g.fillStyle = 'rgba(190,205,230,' + lf.toFixed(3) + ')';
        g.beginPath(); g.moveTo(lx, L.base); g.lineTo(tipX, tipY); g.lineTo(mx, L.base); g.closePath(); g.fill();
        if (faces) faces.push(lx, rx, mx, tipX, tipY);
      });
      if (!faces) return;
      var a = d3 * depth, n, i2;
      // lit faces: pale blue-grey, strongest near the tip
      g.beginPath();
      for (i2 = 0; i2 < faces.length; i2 += 5) { g.moveTo(faces[i2], L.base); g.lineTo(faces[i2 + 3], faces[i2 + 4]); g.lineTo(faces[i2 + 2], L.base); g.closePath(); }
      g.globalAlpha = a * 0.3; g.fillStyle = lg; g.fill();
      // shadow faces: deeper
      g.beginPath();
      for (i2 = 0; i2 < faces.length; i2 += 5) { g.moveTo(faces[i2 + 2], L.base); g.lineTo(faces[i2 + 3], faces[i2 + 4]); g.lineTo(faces[i2 + 1], L.base); g.closePath(); }
      g.globalAlpha = a * 0.32; g.fillStyle = 'rgb(8,14,26)'; g.fill();
      // soft highlights along the ridge and the lit outer edge
      g.beginPath();
      for (i2 = 0; i2 < faces.length; i2 += 5) { g.moveTo(faces[i2], L.base); g.lineTo(faces[i2 + 3], faces[i2 + 4]); g.lineTo(faces[i2 + 2], L.base); }
      g.globalAlpha = a * 0.32; g.strokeStyle = hg; g.lineJoin = 'round'; g.lineWidth = 3 + li * 1.4; g.stroke();
      g.globalAlpha = 1;
    });
  }

  // a few huge, out-of-focus spikes right in front (drawn soft)
  var nearBuf = off(160, 90), nearCtx = nearBuf.getContext('2d');
  var NEAR = [[0.06, 0.3, 0.18], [0.24, 0.36, 0.2], [0.55, 0.28, 0.16], [0.78, 0.34, 0.2], [0.95, 0.3, 0.17]];
  function drawNear(g, t, gust, alpha) {
    nearCtx.clearRect(0, 0, 160, 90);
    nearCtx.fillStyle = '#0b1322';
    NEAR.forEach(function (n, i) {
      var x = ((n[0] * 160 - t / 1000 * 120 + CAM * 0.125) % 190 + 190) % 190 - 15, h = n[1] * 90, w = n[2] * 160 * 0.7, sway = Math.sin(t / 1000 * 1.4 + i) * (2 + 7 * gust);
      nearCtx.beginPath(); nearCtx.moveTo(x - w / 2, 95); nearCtx.lineTo(x + h * 0.35 + sway, 90 - h * 0.8); nearCtx.lineTo(x + w / 2, 95); nearCtx.closePath(); nearCtx.fill();
    });
    g.save(); g.globalAlpha = alpha; g.imageSmoothingQuality = 'high'; g.drawImage(nearBuf, 0, 0, W, H); g.restore();
  }

  // ---- floating specks: pale shards with no weight ----
  var SPECK3 = (function () {
    var r = mulberry32(5150), out = [];
    for (var i = 0; i < 90; i++) out.push({ x: r() * W, y: r() * H, vx: 4 + r() * 12, vy: (r() - 0.5) * 8, rot: r() * 6.28, vr: (r() - 0.5) * 1.2, size: 2 + r() * 5, a: 0.35 + r() * 0.5, ph: r() * 6.28 });
    return out;
  })();
  function drawSpecks3(g, t, gust) {
    var s = t / 1000;
    SPECK3.forEach(function (p) {
      var x = ((p.x + s * p.vx * (1 + 4 * gust)) % W + W) % W;
      var y = ((p.y + s * p.vy + Math.sin(s * 0.8 + p.ph) * 12 - gust * s * 6) % H + H) % H;
      g.save(); g.translate(x, y); g.rotate(p.rot + s * p.vr);
      g.fillStyle = 'rgba(200,214,236,' + p.a.toFixed(3) + ')';
      g.beginPath(); g.moveTo(p.size, 0); g.lineTo(-p.size * 0.7, p.size * 0.45); g.lineTo(-p.size * 0.5, -p.size * 0.4); g.closePath(); g.fill();
      g.restore();
    });
  }

  // ---- the shards the storm lifts: big dark 3D spikes, weightless,
  // drawn up out of the grass and drifting in toward the column ----
  var LIFT = (function () {
    var r = mulberry32(7171), out = [];
    for (var i = 0; i < 90; i++) {
      out.push({ t0: CLIMAX_A + Math.pow(r(), 1.8) * (CLIMAX_B - CLIMAX_A - 2500), x0: r() * W * 1.1 - W * 0.05, y0: H * (0.55 + r() * 0.2),
        rise: 30 + r() * 80, pull: 0.01 + r() * 0.05, swirl: (r() - 0.5) * 2, rot: r() * 6.28, vr: (r() - 0.5) * 0.9, len: 18 + Math.pow(r(), 1.2) * 80, wid: 0.3 + r() * 0.25, z: r() });
    }
    return out;
  })();
  function drawLifted(g, t) {
    LIFT.forEach(function (p) {
      var age = (t - p.t0) / 1000;
      if (age < 0) return;
      var fade = 1 - smooth(ramp(t, CLIMAX_B - 600, CLIMAX_B + 400));
      if (fade <= 0) return;
      // lifted out fast, then hanging: rise eases off, the pull toward the
      // column grows, a slow swirl keeps them turning in the air
      var up = p.rise * (1 - Math.exp(-age * 0.8)) * 3.2 + age * 4;
      var x = p.x0 + (M3X - p.x0) * (1 - Math.exp(-age * p.pull)) + Math.sin(age * 0.7 + p.swirl * 3) * 18 * p.swirl;
      var y = p.y0 - up + Math.cos(age * 0.6 + p.swirl) * 10;
      if (y < -80) return;
      x = ((x % (W + 160)) + W + 160) % (W + 160) - 80;
      var a = Math.min(1, age * 3) * fade * (0.55 + 0.45 * p.z);
      var L = p.len * (0.6 + 0.6 * p.z), Wd = L * p.wid;
      var turn = p.rot + age * p.vr;
      // a two-faced shard: a dark face and a slightly lighter face, so it reads as 3D
      var sq = Math.cos(age * 1.3 + p.swirl * 4);             // tumbling: the visible width breathes
      g.save(); g.translate(x, y); g.rotate(turn); g.globalAlpha = a;
      g.fillStyle = '#121c2e';
      g.beginPath(); g.moveTo(0, -L / 2); g.lineTo(Wd * 0.5 * Math.abs(sq) + 1, L / 2); g.lineTo(0, L * 0.3); g.closePath(); g.fill();
      g.fillStyle = '#2b3a55';
      g.beginPath(); g.moveTo(0, -L / 2); g.lineTo(0, L * 0.3); g.lineTo(-Wd * 0.5, L / 2); g.closePath(); g.fill();
      g.restore();
    });
  }
  // soft drifting cloud-glows of the storm
  var GLOWS3 = (function () {
    var r = mulberry32(6060), out = [];
    for (var i = 0; i < 11; i++) out.push({ x: r() * W, y: H * (0.05 + r() * 0.6), rad: 80 + r() * 120, vx: 10 + r() * 25, a: 0.2 + r() * 0.25, ph: r() * 6.28 });
    return out;
  })();

  function drawMoonScene(t) {
    var g = ctx, s = t / 1000;
    var storm = t < CLIMAX_A ? 0 : t < CLIMAX_B ? 1 : 0;      // the climax state
    var strikeAge = t - CLIMAX_A;
    var settle = storm ? smooth(ramp(strikeAge, 0, 1600)) : 0;
    var gust = storm ? 0.75 + 0.25 * Math.sin(s * 2.3) : 0.15 + 0.1 * Math.sin(s * 0.9);
    var flash = flashAt(t);
    // calm part: the bass gives the big flash (grey wash, spikes fully 3D),
    // the snare a smaller one (facets show faintly, the moon brightens)
    // calm part: each snare is the flash — grey wash, spikes go fully 3D
    var snareF = !storm && t < CLIMAX_A ? flash : 0;
    var bassF = snareF;
    var d3 = snareF;
    var blow = 0;
    BURSTS.forEach(function (b) { blow = Math.max(blow, envelope(t - b, 70, 200, 1700)); });

    // sky: deep navy, turning stormy blue-grey at the strike
    var sk = [Math.round(14 + 22 * settle), Math.round(33 + 18 * settle), Math.round(56 + 26 * settle)];
    g.fillStyle = 'rgb(' + sk.join(',') + ')'; g.fillRect(0, 0, W, H);
    // storm cloud-glows drifting with the wind
    if (settle > 0) {
      GLOWS3.forEach(function (c) {
        var x = ((c.x + s * c.vx * 3) % (W + 300) + W + 300) % (W + 300) - 150;
        var gr = g.createRadialGradient(x, c.y, 0, x, c.y, c.rad);
        gr.addColorStop(0, 'rgba(200,212,232,' + (c.a * settle * (0.8 + 0.2 * Math.sin(s + c.ph))).toFixed(3) + ')'); gr.addColorStop(1, 'rgba(200,212,232,0)');
        g.fillStyle = gr; g.fillRect(x - c.rad, c.y - c.rad, c.rad * 2, c.rad * 2);
      });
    }
    // crisp stepped rings around the moon; they swell a little on each snare
    var ringK = (storm ? 0.55 : 1) * (0.75 + 0.35 * flash);
    // once the moon is shut off after the climax, it stays off
    var moonOn = 1 - smooth(ramp(t, CLIMAX_B + 400, CLIMAX_B + 2200));
    for (var i = 9; i >= 1 && moonOn > 0; i--) {
      var u = i / 9, rr = M3R * (1.05 + 1.2 * u);
      var l = 1 - u;
      var c = [sk[0] + (118 - sk[0]) * l * 0.9, sk[1] + (130 - sk[1]) * l * 0.9, sk[2] + (158 - sk[2]) * l * 0.9].map(Math.round);
      g.fillStyle = 'rgba(' + c.join(',') + ',' + Math.min(1, 0.55 * ringK + 0.25).toFixed(3) + ')';
      g.beginPath(); g.arc(M3X, M3Y, rr, 0, 6.283); g.fill();
    }
    // the two orbs that fall toward the moon just before the strike
    // five orbs, falling in twice as fast as before
    [[0, 0.88, -0.05], [1, 0.72, -0.12], [2, 0.98, 0.18], [3, 0.30, -0.10], [4, 0.12, 0.10]].forEach(function (o) {
      var a0 = CLIMAX_A - 950 + o[0] * 90, k = ramp(t, a0, CLIMAX_A + 75);
      if (k <= 0 || k >= 1) return;
      var x = W * o[1] + (M3X - W * o[1]) * k * k, y = H * o[2] + (M3Y - H * 0.1 - H * o[2]) * k * k;
      var gr = g.createRadialGradient(x, y, 0, x, y, 36);
      gr.addColorStop(0, 'rgba(255,255,250,0.95)'); gr.addColorStop(0.25, 'rgba(240,244,250,0.7)'); gr.addColorStop(1, 'rgba(210,220,240,0)');
      g.fillStyle = gr; g.fillRect(x - 36, y - 36, 72, 72);
    });
    // burst orbs + soft glows from each explosion (behind the grass)
    g.save(); g.globalCompositeOperation = 'lighter';
    BURSTS.forEach(function (b, bi) {
      var age0 = (t - b) / 1000;
      if (age0 < 0 || age0 > 4) return;
      var set = ORB_SEEDS[bi];
      set.glows.forEach(function (o) {
        var age = age0 - o.d; if (age < 0 || age > 3.2) return;
        var dist = o.sp * (1 - Math.exp(-0.4 * age)) / 0.4, x = M3X + Math.cos(o.a) * dist, y = M3Y + Math.sin(o.a) * dist;
        var al = o.al * Math.max(0, 1 - age / 3.2) * Math.min(1, age * 12);
        var gg = g.createRadialGradient(x, y, 0, x, y, o.rad);
        gg.addColorStop(0, 'rgba(210,222,245,' + al.toFixed(3) + ')'); gg.addColorStop(1, 'rgba(190,205,235,0)');
        g.fillStyle = gg; g.beginPath(); g.arc(x, y, o.rad, 0, 6.283); g.fill();
      });
      set.orbs.forEach(function (o, oi) {
        if (oi % 2) return; // fewer bullets than the old draft: the lifted shards carry the scene
        var age = age0 - o.d; if (age < 0) return;
        var dist = o.sp * (1 - Math.exp(-0.12 * age)) / 0.12, x = M3X + Math.cos(o.a) * (M3R * 0.2 + dist), y = M3Y + Math.sin(o.a) * (M3R * 0.2 + dist);
        if (x < -40 || x > W + 40 || y < -40 || y > H + 40) return;
        var al = o.al * Math.min(1, age * 12);
        var og = g.createRadialGradient(x, y, 0, x, y, o.s * 3.2);
        og.addColorStop(0, 'rgba(255,255,255,' + al.toFixed(3) + ')'); og.addColorStop(1, 'rgba(210,225,250,0)');
        g.fillStyle = og; g.beginPath(); g.arc(x, y, o.s * 3.2, 0, 6.283); g.fill();
      });
    });
    g.restore();
    // the moon: warm cream, blowing out on each explosion
    var mr = M3R * (1 + 0.05 * blow);
    var core = 'rgb(' + [244, 232, 212].map(function (c) { return Math.round(c + (255 - c) * Math.max(blow, settle * 0.6)); }).join(',') + ')';
    g.globalAlpha = moonOn; g.fillStyle = core; g.beginPath(); g.arc(M3X, M3Y, mr, 0, 6.283); g.fill(); g.globalAlpha = 1;
    var glow = g.createRadialGradient(M3X, M3Y, mr * 0.98, M3X, M3Y, mr * (1.12 + 0.7 * settle + 0.4 * Math.max(bassF, 0.6 * snareF)));
    var mf = 0.55 * Math.max(bassF, 0.6 * snareF);   // snare flash, calm part only
    glow.addColorStop(0, 'rgba(255,244,226,' + Math.min(1, 0.06 + 0.6 * Math.max(blow, settle) + 0.75 * mf).toFixed(3) + ')'); glow.addColorStop(1, 'rgba(255,252,244,0)');
    g.save(); g.globalAlpha = moonOn; g.globalCompositeOperation = 'lighter'; g.fillStyle = glow; g.fillRect(0, 0, W, H); g.restore();
    // the strike: rays bursting out of the moon for the first ~1.5 s
    var rays = storm ? Math.max(0, 1 - strikeAge / 1500) * Math.min(1, strikeAge / 80) : 0;
    if (rays > 0) {
      g.save(); g.globalCompositeOperation = 'lighter';
      var rr = mulberry32(99);
      for (var k = 0; k < 22; k++) {
        var ang = -Math.PI * (0.05 + 0.9 * rr()), wdt = 0.04 + rr() * 0.06, len = M3R * (1.6 + rr() * 1.6);
        g.fillStyle = 'rgba(240,244,252,' + (rays * (0.18 + rr() * 0.25)).toFixed(3) + ')';
        g.beginPath(); g.moveTo(M3X, M3Y);
        g.lineTo(M3X + Math.cos(ang - wdt) * len, M3Y + Math.sin(ang - wdt) * len);
        g.lineTo(M3X + Math.cos(ang + wdt) * len, M3Y + Math.sin(ang + wdt) * len); g.closePath(); g.fill();
      }
      g.restore();
    }
    // the column: whips left and right, foot in the moon
    var column = t < CLIMAX_A ? 0 : t < CLIMAX_B ? Math.min(1, (t - CLIMAX_A) / 60) : Math.max(0, 1 - Math.pow((t - CLIMAX_B) / 1100, 2));
    if (column > 0.01) {
      var sw = sway(t), drop = clamp((t - CLIMAX_A) / 90, 0, 1);
      g.save(); g.globalCompositeOperation = 'lighter';
      for (var st = 0; st < COLUMN_STEPS; st++) {
        var uu = st / (COLUMN_STEPS - 1);
        g.strokeStyle = uu > 0.9 ? '#fffbef' : 'rgb(' + Math.round(200 + 50 * uu) + ',' + Math.round(214 + 36 * uu) + ',' + Math.round(240 + 8 * uu) + ')';
        g.globalAlpha = column * (0.018 + 0.1 * Math.pow(uu, 3) + (uu > 0.9 ? 0.35 : 0));
        g.lineWidth = M3R * (1.7 - 1.42 * Math.pow(uu, 0.75));
        var footY = COLUMN_TOP + (COLUMN_BOTTOM - COLUMN_TOP) * drop;
        g.beginPath(); g.moveTo(M3X + sw.lean, COLUMN_TOP);
        g.quadraticCurveTo(M3X + sw.lean * sw.bend, (COLUMN_TOP + footY) / 2, M3X, footY); g.stroke();
      }
      g.restore();
    }
    // the shards the storm lifts, then the spike field over them
    drawLifted(g, t);
    var ground = g.createLinearGradient(0, H * 0.6, 0, H);
    ground.addColorStop(0, 'rgba(' + Math.round(20 + 30 * settle) + ',' + Math.round(32 + 32 * settle) + ',' + Math.round(54 + 36 * settle) + ',0)');
    ground.addColorStop(0.25, 'rgb(' + Math.round(20 + 30 * settle) + ',' + Math.round(32 + 32 * settle) + ',' + Math.round(54 + 36 * settle) + ')');
    ground.addColorStop(1, 'rgb(10,18,32)');
    g.fillStyle = ground; g.fillRect(0, H * 0.6, W, H * 0.4);
    var lit = storm ? 0.05 + 0.4 * (1 - settle) + 0.12 * flash : 0.04 * flash;
    drawField(g, t, gust, lit, d3);
    // light from behind, through the grass, during the storm
    if (settle > 0) {
      var thru = g.createRadialGradient(M3X, M3Y, M3R * 0.5, M3X, M3Y + H * 0.05, W * 0.32);
      thru.addColorStop(0, 'rgba(225,232,245,' + (0.22 * settle).toFixed(3) + ')'); thru.addColorStop(1, 'rgba(225,232,245,0)');
      g.save(); g.globalCompositeOperation = 'lighter'; g.fillStyle = thru; g.fillRect(0, 0, W, H); g.restore();
    }
    drawSpecks3(g, t, gust);
    drawNear(g, t, gust, 0.6);
    // the grey haze the storm hangs in
    // snare flash. In the storm: a light wash. Calm: the whole scene washes
    // into a soft pale haze — blurred, greyed — with the moon blooming
    if (flash > 0.01 && storm) {
      g.save(); g.globalCompositeOperation = 'lighter';
      g.fillStyle = 'rgba(205,212,222,' + (flash * 0.22).toFixed(3) + ')'; g.fillRect(0, 0, W, H); g.restore();
    } else if (bassF > 0.01) {
      // the grey wash, on the bass only — light, so the 3D spikes still read through it
      hazeCtx.drawImage(canvas, 0, 0, 213, 120);
      g.save(); g.globalAlpha = bassF * 0.35; g.imageSmoothingQuality = 'high'; g.drawImage(hazeBuf, 0, 0, W, H); g.restore();
      g.fillStyle = 'rgba(120,134,152,' + (bassF * 0.22).toFixed(3) + ')'; g.fillRect(0, 0, W, H);
    }
    // after the climax: the moon is shut off, but the field stays faintly
    // visible — drained to grey, blurred, sinking to near-black with soft
    // grey glows hanging in it, then the spikes come back dimly and linger
    // through the breakdown until the outro fades it all out
    var after = t - CLIMAX_B;
    if (after > 300) {
      // brightness: 0.5 → near-black (by +1.6 s) → back up to a dim 0.3 (+3.5 s on)
      var down = smooth(ramp(after, 700, 1500)), up = smooth(ramp(after, 2200, 3800));
      var bright = 0.42 - 0.38 * down + 0.44 * up;
      var blur = 1 - smooth(ramp(after, 2600, 4200));       // soft, then the shapes return
      afterCtx.drawImage(canvas, 0, 0, 320, 180);
      snapCtx.clearRect(0, 0, W, H); snapCtx.drawImage(canvas, 0, 0);
      g.save();
      g.fillStyle = '#000'; g.fillRect(0, 0, W, H);
      g.filter = 'grayscale(1) brightness(' + bright.toFixed(3) + ') contrast(1.1)';
      g.globalAlpha = 1 - blur * 0.7; g.drawImage(snapBuf, 0, 0);
      g.globalAlpha = blur * 0.85 + 0.15; g.drawImage(afterBuf, 0, 0, W, H);
      g.restore();
      // soft grey glows drifting in the dark
      var glowA = (0.35 * down + 0.15) * (1 - 0.15 * up);
      g.save(); g.globalCompositeOperation = 'lighter';
      GHOSTS.forEach(function (c) {
        var x = ((c.x + s * c.vx) % (W + 300) + W + 300) % (W + 300) - 150, y = c.y + Math.sin(s * 0.4 + c.ph) * 14;
        var gr = g.createRadialGradient(x, y, 0, x, y, c.rad);
        gr.addColorStop(0, 'rgba(120,118,114,' + (c.a * glowA).toFixed(3) + ')'); gr.addColorStop(1, 'rgba(120,118,114,0)');
        g.fillStyle = gr; g.fillRect(x - c.rad, y - c.rad, c.rad * 2, c.rad * 2);
      });
      g.restore();
      g.fillStyle = 'rgba(200,205,212,' + (0.45 * down).toFixed(3) + ')';
      for (var q = 0; q < 26; q++) { var px = ((hash(q * 3) * W + s * 7) % W), py = hash(q * 3 + 1) * H; g.fillRect(px, py, 2, 2); }
    }
    // whiteouts: the strike, and the end of the climax
    var white = Math.max(storm ? 1 - smooth(ramp(strikeAge, 120, 1400)) : 0, envelope(t - CLIMAX_B, 120, 220, 450));
    if (white > 0) { g.fillStyle = 'rgba(250,251,253,' + Math.min(1, white).toFixed(3) + ')'; g.fillRect(0, 0, W, H); }
    // arriving: from dark grey through a white fog that clears onto the moon
    if (t < ARRIVE + 2200 && (MODE === 'full' || t >= ARRIVE)) {
      // a white flash that clears through pale fog onto the moon
      // hold white through the whole first bass drum, then clear
      var wf = 1 - smooth(ramp(t, ARRIVE + 40, ARRIVE + 340));
      g.fillStyle = 'rgba(244,245,247,' + Math.min(1, wf * 1.05).toFixed(3) + ')'; g.fillRect(0, 0, W, H);
    }
  }
  var afterBuf = off(320, 180), afterCtx = afterBuf.getContext('2d');
  var hazeBuf = off(213, 120), hazeCtx = hazeBuf.getContext('2d');
  var snapBuf = off(), snapCtx = snapBuf.getContext('2d');
  var GHOSTS = (function () {
    var r = mulberry32(4444), out = [];
    for (var i = 0; i < 18; i++) out.push({ x: r() * W, y: r() * H, rad: 40 + r() * 70, vx: 4 + r() * 10, a: 0.4 + r() * 0.6, ph: r() * 6.28 });
    return out;
  })();

  // Scene 3 only: the moon scene under the intro song, veiled; dark through the silence;
  // dark grey rising; then the white flash on the first drum of the drop.
  function renderScene3(t) {
    if (t >= T.black && t < ARRIVE) {
      var gl = Math.round(58 * smooth(ramp(t, T.black + 150, ARRIVE - 100)));
      ctx.fillStyle = 'rgb(' + gl + ',' + gl + ',' + gl + ')'; ctx.fillRect(0, 0, W, H);
      return;
    }
    drawMoonScene(t);
    if (t < T.black) {
      var veil = t < T.grey ? 1 - 0.55 * smooth(ramp(t, 0, 3000)) : 0.45 + 0.55 * smooth(ramp(t, T.grey, T.black));
      ctx.fillStyle = 'rgba(0,0,0,' + veil.toFixed(3) + ')'; ctx.fillRect(0, 0, W, H);
    }
  }

  // ---------- director ----------
  function render(t) {
    if (MODE === 'scene3') renderScene3(t);
    else if (t < T.grey) drawIntro(t);
    else if (t < T.g1End) {
      // glitch 1: the intro smeared into streaks, with the line
      drawGlitch(t, t - T.grey, T.g1End - T.grey, function () { drawIntro(T.introEnd); }, 'intro', true, 0.6, 0.38);
    } else if (t < T.black) { ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H); }
    else if (t < T.glitchA) drawMountains(t);
    else if (t < T.glitchB) {
      // glitch 2: the haze smeared, wavy then straightening, no line
      var since = t - T.glitchA, dur = T.glitchB - T.glitchA;
      drawGlitch(t, since, dur, function () { drawMountains(T.glitchA - 1); }, 'storm', false, 0.6 * (1 - smooth(ramp(since, 400, 1500))), 1.0, true);
    } else if (t < T.black2) {
      // black, then slowly rising to dark grey before the white flash
      var gl = Math.round(58 * smooth(ramp(t, T.glitchB + 150, T.black2 - 100)));
      ctx.fillStyle = 'rgb(' + gl + ',' + gl + ',' + gl + ')'; ctx.fillRect(0, 0, W, H);
    }
    else drawMoonScene(t);
    if (t > T.outroA) {
      var o = smooth(ramp(t, T.outroA, T.outroB));
      ctx.fillStyle = 'rgba(0,0,0,' + o.toFixed(3) + ')'; ctx.fillRect(0, 0, W, H);
    }
  }


  return {
    render: function (t, cam, shear) {
      CAM = cam || 0;
      SHEAR = shear || 0;
      render(t);
    },
    setMode: function (m) {
      if (m === MODE) return;
      MODE = m;
      applyMode();
    },
  };
}
