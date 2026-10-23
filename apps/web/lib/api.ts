import { supabaseBrowser } from "@/lib/supabase/client";
import type { components } from "@/lib/types.gen";

export type CheckReport = components["schemas"]["CheckReport"];
export type Finding = components["schemas"]["Finding"];

const CHECKER = process.env.NEXT_PUBLIC_CHECKER_URL!;
const HEALTH_TIMEOUT_MS = 8_000;
const RETRY_DELAYS_MS = [2_000, 4_000, 8_000]; // 3 retries: ~46 s budget covers a ~25 s cold start
const CHECK_TIMEOUT_MS = 90_000; // full reports with AI may take up to ~60 s

export class CheckError extends Error {
  constructor(
    public code: string,
    message: string,
  ) {
    super(message);
  }
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

async function fetchWithTimeout(url: string, init: RequestInit, ms: number) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), ms);
  try {
    return await fetch(url, { ...init, signal: ctrl.signal });
  } finally {
    clearTimeout(timer);
  }
}

/**
 * The free checker sleeps when idle. Wake it with /health first (cheap, 8 s timeout, retried),
 * so a slow-but-working check is never mistaken for a sleeping server.
 */
async function ensureAwake(onWaking: (waking: boolean) => void) {
  for (let attempt = 0; attempt <= RETRY_DELAYS_MS.length; attempt++) {
    try {
      const r = await fetchWithTimeout(`${CHECKER}/health`, {}, HEALTH_TIMEOUT_MS);
      if (r.ok) {
        onWaking(false);
        return;
      }
    } catch {
      // timeout or network error: the server is probably starting up
    }
    onWaking(true);
    if (attempt < RETRY_DELAYS_MS.length) await sleep(RETRY_DELAYS_MS[attempt]);
  }
  onWaking(false);
  throw new CheckError("unavailable", "The checker didn't wake up. Wait a minute and try again.");
}

async function authHeader(): Promise<Record<string, string>> {
  const { data } = await supabaseBrowser().auth.getSession();
  const token = data.session?.access_token;
  if (!token) throw new CheckError("unauthorized", "Your session has ended. Sign in again.");
  return { Authorization: `Bearer ${token}` };
}

async function request<T>(path: string, init: RequestInit, onWaking: (w: boolean) => void): Promise<T> {
  const headers = { ...(await authHeader()), ...(init.headers as Record<string, string> | undefined) };
  await ensureAwake(onWaking);
  let r: Response;
  try {
    r = await fetchWithTimeout(`${CHECKER}${path}`, { ...init, headers }, CHECK_TIMEOUT_MS);
  } catch {
    throw new CheckError("timeout", "The checker took too long. Try again.");
  }
  if (r.ok) return (await r.json()) as T;
  const body = await r.json().catch(() => null);
  throw new CheckError(
    body?.code ?? `http_${r.status}`,
    body?.message ?? "Something went wrong on the checker. Try again.",
  );
}

export function check(form: FormData, onWaking: (waking: boolean) => void = () => {}) {
  return request<CheckReport>("/v1/checks", { method: "POST", body: form }, onWaking);
}

/** Apply accepted fixes and edits (finding record ids) on the server, then re-check. */
export function applyFixes(
  versionId: string,
  accepted: string[],
  edits: Record<string, string>,
  onWaking: (waking: boolean) => void = () => {},
) {
  return request<CheckReport>(
    `/v1/versions/${versionId}/apply`,
    { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ accepted, edits }) },
    onWaking,
  );
}

export function dismissFinding(recordId: string, reason: string) {
  return request<{ ok: boolean }>(
    `/v1/findings/${recordId}/decisions`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "dismiss", reason }),
    },
    () => {},
  );
}

export function submitForReview(contentId: string, onWaking: (waking: boolean) => void = () => {}) {
  return request<CheckReport>(`/v1/contents/${contentId}/submit`, { method: "POST" }, onWaking);
}
