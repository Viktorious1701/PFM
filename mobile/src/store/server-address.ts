/**
 * Where the API lives. The family's server is a laptop behind a free
 * Cloudflare quick tunnel whose address changes on every start
 * (constitution ENV-06), so the address is a per-device setting rather than
 * something baked into the build: typed on the sign-in screen, or carried in
 * an invitation link (`pfm://activate?token=…&server=…`).
 *
 * `EXPO_PUBLIC_API_BASE_URL` is the default (the dev backend on web). The
 * value `none` means "no default": the sign-in screen asks for one.
 */
import { useSyncExternalStore } from 'react';

import { API_BASE_URL } from '../config';
import { readSetting, writeSetting } from './device-storage';

const KEY = 'pfm.server';
const API_PATH = '/api/v1';

let current: string | null = API_BASE_URL || null;
let chosen = false; // set this session, so the stored value must not override it
const listeners = new Set<() => void>();
// Deferred, so setting the address while a screen renders (an invitation
// link's `server`) never updates another component mid-render.
const notify = () => queueMicrotask(() => listeners.forEach((l) => l()));

const loaded = readSetting(KEY).then((stored) => {
  if (stored && !chosen) {
    current = stored;
    notify();
  }
});

/**
 * Turns what someone typed or pasted into an API base URL:
 * `abc.trycloudflare.com` → `https://abc.trycloudflare.com/api/v1`.
 * Returns null for something that isn't an http(s) address.
 */
export function normalizeServerAddress(input: string): string | null {
  let s = input.trim();
  if (!s) return null;
  if (!/^[a-z][a-z0-9+.-]*:\/\//i.test(s)) s = `https://${s}`;
  // Parsed by hand: React Native's URL implementation is incomplete.
  const m = /^(https?):\/\/([a-z0-9.-]+(?::\d+)?)(\/[^?#]*)?(?:[?#].*)?$/i.exec(s);
  if (!m) return null;
  const path = (m[3] ?? '').replace(/\/+$/, '');
  return `${m[1].toLowerCase()}://${m[2].toLowerCase()}${path.endsWith(API_PATH) ? path : path + API_PATH}`;
}

/** The API base URL, once any stored address has been read. */
export async function serverAddress(): Promise<string | null> {
  await loaded;
  return current;
}

/** Sets and remembers the address. Returns false if it isn't one. */
export function setServerAddress(input: string): boolean {
  const next = normalizeServerAddress(input);
  if (!next) return false;
  chosen = true;
  if (next !== current) {
    current = next;
    notify();
  }
  void writeSetting(KEY, next);
  return true;
}

function subscribe(l: () => void) {
  listeners.add(l);
  return () => listeners.delete(l);
}

/** The current address, for showing on screen; re-renders when it changes. */
export function useServerAddress(): string | null {
  return useSyncExternalStore(subscribe, () => current, () => current);
}

/** `https://abc.trycloudflare.com/api/v1` → `abc.trycloudflare.com`. */
export function serverHost(address: string): string {
  return /^[a-z]+:\/\/([^/]+)/i.exec(address)?.[1] ?? address;
}
