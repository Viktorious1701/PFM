/**
 * The glitch — a port of the validated "Moonlit Glitch" study (artifact
 * AmMLNktMoQrbVoZK5phnwe), with the values chosen there: 1.0 s long, wave
 * bend 5%, smear length 20%, taking over 30%, stutter in/out, and the line
 * "get out of my head".
 *
 * The smear stretches a short slice of every 3-unit row band across the
 * whole width, sampling a grey copy of the scene (flat grey sky,
 * near-black blades) whose slice position drifts along slow sine waves, so
 * blade silhouettes become long dark bending streaks. That is per-pixel
 * work, so it is drawn on a <canvas>, not in the SVG scene. Web only (the
 * app's one run target, constitution ENV-04); elsewhere this renders
 * nothing.
 *
 * Fired by the caller (`ref.current.fire()`); between glitches the canvas
 * is hidden and nothing runs.
 */
import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef } from 'react';
import { Platform, StyleSheet, View, type LayoutChangeEvent } from 'react-native';

import { coverFit, GRASS, grassBlades, H, MOON_CX, MOON_CY, MOON_R, W } from './moonGeometry';

export type GlitchHandle = { fire: () => void };

const DURATION_MS = 1000;
const BEND = 0.05;
const SMEAR_LEN = 0.2;
const TAKEOVER = 0.3;
const WORDS = 'get out of my head';
const GREY_GRASS = ['#383838', '#222222', '#0e0e0e']; // far, mid, near

/** The scene redrawn in the glitch's palette — what the smear samples. */
function greyScene(): HTMLCanvasElement {
  const c = document.createElement('canvas');
  c.width = W;
  c.height = H;
  const g = c.getContext('2d')!;
  g.fillStyle = '#444444';
  g.fillRect(0, 0, W, H);
  const moon = g.createRadialGradient(MOON_CX, MOON_CY, 0, MOON_CX, MOON_CY, MOON_R * 1.6);
  moon.addColorStop(0, '#5a5a5a');
  moon.addColorStop(0.6, '#525252');
  moon.addColorStop(1, 'rgba(68,68,68,0)');
  g.fillStyle = moon;
  g.fillRect(0, 0, W, H);
  GRASS.forEach((spec, li) => {
    g.fillStyle = GREY_GRASS[li];
    for (const k of [-1, 0, 1]) {
      for (const b of grassBlades(spec)) {
        const x = b.x + k * W;
        if (x < -100 || x > W + 100) continue;
        g.beginPath();
        g.moveTo(x - b.w / 2, spec.baseY);
        g.lineTo(x + b.tipDX, b.tipY);
        g.lineTo(x + b.w / 2, spec.baseY);
        g.closePath();
        g.fill();
      }
    }
  });
  return c;
}

/** How much of the glitch shows `since` ms in: stutters on/off for the
 * first ~320 ms and last ~220 ms; the words fade in and out inside. */
function stateAt(since: number) {
  let on = 1;
  let shiver = 0;
  if (since < 320) {
    on = Math.floor(since / 55) % 2 === 0 ? 1 : since < 160 ? 0 : 0.5;
    shiver = (Math.random() - 0.5) * 10;
  }
  if (since > DURATION_MS - 220) {
    on = Math.floor((DURATION_MS - since) / 50) % 2 === 0 ? 1 : 0;
    shiver = (Math.random() - 0.5) * 10;
  }
  const wIn = 420;
  const wOut = DURATION_MS - 380;
  const words =
    since < wIn ? 0 : since < wIn + 500 ? (since - wIn) / 500 : since < wOut - 400 ? 1 : since < wOut ? (wOut - since) / 400 : 0;
  return { on, words: Math.max(0, words), shiver };
}

function GlitchOverlayImpl(_: object, ref: React.Ref<GlitchHandle>) {
  const host = useRef<View>(null);
  const canvas = useRef<HTMLCanvasElement | null>(null);
  const smear = useRef<HTMLCanvasElement | null>(null);
  const grey = useRef<HTMLCanvasElement | null>(null);
  const raf = useRef(0);
  const size = useRef<{ w: number; h: number } | null>(null);

  // Same cover-fit as the scene, so streaks line up with the real grass.
  const place = useCallback(() => {
    const c = canvas.current;
    if (!c || !size.current) return;
    const { scale, offX, offY } = coverFit(size.current.w, size.current.h);
    Object.assign(c.style, { left: `${offX}px`, top: `${offY}px`, width: `${W * scale}px`, height: `${H * scale}px` });
  }, []);

  useEffect(() => {
    if (Platform.OS !== 'web') return;
    const el = host.current as unknown as HTMLElement | null;
    if (!el) return;
    const c = document.createElement('canvas');
    c.width = W;
    c.height = H;
    Object.assign(c.style, { position: 'absolute', display: 'none', pointerEvents: 'none' });
    el.appendChild(c);
    canvas.current = c;
    const m = document.createElement('canvas');
    m.width = W;
    m.height = H;
    smear.current = m;
    grey.current = greyScene();
    place();
    return () => {
      cancelAnimationFrame(raf.current);
      c.remove();
    };
  }, [place]);

  const onLayout = useCallback(
    (e: LayoutChangeEvent) => {
      size.current = { w: e.nativeEvent.layout.width, h: e.nativeEvent.layout.height };
      place();
    },
    [place],
  );

  const fire = useCallback(() => {
    const c = canvas.current;
    const m = smear.current;
    const src = grey.current;
    if (!c || !m || !src) return;
    const ctx = c.getContext('2d')!;
    const mctx = m.getContext('2d')!;
    cancelAnimationFrame(raf.current);
    c.style.display = 'block';
    const start = performance.now();

    const frame = (now: number) => {
      const since = now - start;
      ctx.clearRect(0, 0, W, H);
      if (since >= DURATION_MS) {
        c.style.display = 'none';
        return;
      }
      const st = stateAt(since);
      if (st.on > 0) {
        mctx.clearRect(0, 0, W, H);
        for (let y = 0; y < H; y += 3) {
          const phase = y * 0.011 + now * 0.0011;
          const sw = 10 + (1 - SMEAR_LEN) * 260 + 24 * (0.5 + 0.5 * Math.sin(y * 0.05 + now * 0.0009));
          let sx = W * 0.5 + Math.sin(phase) * W * 0.32 * BEND + Math.sin(y * 0.037 - now * 0.0017) * W * 0.06 * BEND;
          sx = Math.max(0, Math.min(W - sw, sx));
          // rows come from where the grass tips are: sparse blades with
          // grey between them (the dense base smears to solid black)
          let sy = H * 0.24 + y * 0.42 + Math.sin(y * 0.02 + now * 0.0013) * 34 * BEND;
          sy = Math.max(0, Math.min(H - 3, sy));
          const dx = -W * 0.35 + Math.sin(phase * 0.8 + 1.3) * W * 0.25 * BEND;
          mctx.drawImage(src, sx, sy, sw, 3, dx, y, W * 1.7, 3);
        }
        ctx.globalAlpha = st.on * TAKEOVER;
        ctx.drawImage(m, 0, 0);
        ctx.globalAlpha = 1;
      }
      if (st.words > 0.01) {
        ctx.save();
        ctx.font = '64px "CormorantGaramond_300Light", Georgia, serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        if ('letterSpacing' in ctx) (ctx as unknown as { letterSpacing: string }).letterSpacing = '6px';
        const x = W / 2 + st.shiver;
        const y = H / 2 + 10;
        ctx.fillStyle = `rgba(205,205,205,${(st.words * 0.22).toFixed(3)})`;
        ctx.fillText(WORDS, x - 4, y + 2);
        ctx.fillText(WORDS, x + 3, y - 1);
        ctx.fillStyle = `rgba(160,160,160,${(st.words * 0.85).toFixed(3)})`;
        ctx.fillText(WORDS, x, y);
        ctx.restore();
      }
      raf.current = requestAnimationFrame(frame);
    };
    raf.current = requestAnimationFrame(frame);
  }, []);

  useImperativeHandle(ref, () => ({ fire }), [fire]);

  if (Platform.OS !== 'web') return null;
  return <View ref={host} style={StyleSheet.absoluteFill} pointerEvents="none" onLayout={onLayout} />;
}

export const GlitchOverlay = forwardRef(GlitchOverlayImpl);
