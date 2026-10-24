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

// Render's proxy answers 502/503/504 (not our JSON) while the service restarts or wakes.
const GATEWAY = new Set([502, 503, 504]);
const isCheckerError = (r: Response) =>
  r.clone().json().then((b) => typeof b?.code === "string", () => false);

async function request<T>(path: string, init: RequestInit, onWaking: (w: boolean) => void): Promise<T> {
  const headers = { ...(await authHeader()), ...(init.headers as Record<string, string> | undefined) };
  await ensureAwake(onWaking);
  const send = async () => {
    try {
      return await fetchWithTimeout(`${CHECKER}${path}`, { ...init, headers }, CHECK_TIMEOUT_MS);
    } catch {
      throw new CheckError("timeout", "The checker took too long. Try again.");
    }
  };
  let r = await send();
  if (GATEWAY.has(r.status) && !(await isCheckerError(r))) {
    // The request never reached the checker: wait for it to wake, then try once more.
    onWaking(true);
    await sleep(RETRY_DELAYS_MS[0]);
    await ensureAwake(onWaking);
    r = await send();
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

/** The writer passes a blocking finding they can't fix to a reviewer. */
export function escalateFinding(recordId: string, reason: string) {
  return request<{ ok: boolean }>(
    `/v1/findings/${recordId}/decisions`,
    { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action: "escalate", reason }) },
    () => {},
  );
}

export type QueueRow = {
  version_id: string;
  content_id: string;
  n: number;
  title: string | null;
  channel: string | null;
  origin: string | null;
  status: string;
  submitted_at: string;
  author: string;
  blocking: number;
  claims: number;
  required: string[];
  approved: string[];
  pending: string[];
};

export type ReviewDetail = {
  version: { id: string; content_id: string; n: number; text: string; status: string; created_at: string };
  content: { id: string; title: string | null; channel: string | null; origin: string | null };
  report: CheckReport;
  state: { required: string[]; approved: string[]; pending: string[]; undecided_blocking: string[]; overruled: string[] };
  decisions: { finding_id: string; action: string; reason: string | null; at: string; who: string }[];
  comments: { body: string; created_at: string; who: string }[];
  timeline: { at: string; who: string; what: string; reason?: string | null }[];
  can_decide: string[];
  can_approve: string[];
};

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const review = {
  queue: (onWaking: (w: boolean) => void = () => {}) => request<QueueRow[]>("/v1/review/queue", {}, onWaking),
  get: (versionId: string, onWaking: (w: boolean) => void = () => {}) =>
    request<ReviewDetail>(`/v1/review/${versionId}`, {}, onWaking),
  decide: (versionId: string, recordId: string, action: "uphold" | "overrule", reason: string) =>
    request<ReviewDetail>(`/v1/review/${versionId}/decisions`, json({ record_id: recordId, action, reason }), () => {}),
  approve: (versionId: string, stage: string, outcome: "approve" | "request_changes", reason?: string) =>
    request<ReviewDetail>(`/v1/versions/${versionId}/approve`, json({ stage, outcome, reason }), () => {}),
  comment: (versionId: string, body: string) => request<ReviewDetail>(`/v1/review/${versionId}/comments`, json({ body }), () => {}),
};

export type AuditEvent = {
  id: number;
  at: string;
  who: string;
  what: string;
  reason: string | null;
  kind: string;
  entity_id: string | null;
  hash: string;
};
export type AuditVerify = {
  scope: "org" | "mine";
  valid: boolean | null; // null: a creator's view has gaps, so it can't be verified
  length: number;
  broken_at: number | null;
  recent: AuditEvent[];
};

export const audit = {
  verify: (onWaking: (w: boolean) => void = () => {}) => request<AuditVerify>("/v1/audit/verify", {}, onWaking),
  /** Downloads the whole chain as CSV (the browser can't attach the token to a plain link). */
  async exportCsv() {
    const r = await fetch(`${CHECKER}/v1/audit/export.csv`, { headers: await authHeader() });
    if (!r.ok) throw new CheckError(`http_${r.status}`, "Couldn't export the audit log. Try again.");
    const url = URL.createObjectURL(await r.blob());
    const a = document.createElement("a");
    a.href = url;
    a.download = "plumbline-audit.csv";
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1_000);
  },
};

export type RuleRow = {
  id: string;
  title: string;
  category: string;
  cls: "A" | "B" | "C";
  check_type: string;
  severity: string;
  tier: "mandatory" | "brand";
  maturity: "advisory" | "blocking";
  source_ref: string;
  owner_function: string;
  warnings: string[];
};
export type RulesResponse = { rulebook_version: string; can_import: boolean; rules: RuleRow[] };
export type ImportResult = {
  dry_run: boolean;
  imported: number;
  need_clarification: number;
  warnings: Record<string, string[]>;
  rejected: string[];
};
export type Wording = { id: string; fact_id: string; market: string; channel: string; text: string; disclaimer: string | null };
export type FactRow = {
  id: string;
  statement: string;
  product: string | null;
  market: string;
  owner: string;
  valid_from: string;
  valid_until: string | null;
  confidentiality: "public" | "internal" | "confidential" | "embargoed";
  embargo_until: string | null;
  verified: boolean;
  expired: boolean;
  wordings: Wording[];
};
export type FactsResponse = { today: string; restricted: boolean; facts: FactRow[] };

/** Rule titles for the finding cards. A nice-to-have, so it never probes or waits for a sleeping checker
 * (the check itself does that) and any failure just leaves the cards with their rule codes. */
export async function ruleTitles(): Promise<Record<string, string>> {
  try {
    const r = await fetchWithTimeout(`${CHECKER}/v1/rules`, { headers: await authHeader() }, HEALTH_TIMEOUT_MS * 2);
    if (!r.ok) return {};
    const body = (await r.json()) as RulesResponse;
    return Object.fromEntries(body.rules.map((x) => [x.id, x.title]));
  } catch {
    return {};
  }
}

export const rulebook = {
  rules: (onWaking: (w: boolean) => void = () => {}) => request<RulesResponse>("/v1/rules", {}, onWaking),
  importCsv: (file: File, dryRun: boolean) => {
    const form = new FormData();
    form.set("file", file);
    return request<ImportResult>(`/v1/rules/import?dry_run=${dryRun}`, { method: "POST", body: form }, () => {});
  },
  facts: (onWaking: (w: boolean) => void = () => {}) => request<FactsResponse>("/v1/facts", {}, onWaking),
};

export type HealthRow = {
  rule_id: string;
  title: string | null;
  tier: "mandatory" | "brand" | null;
  maturity: "advisory" | "blocking" | null;
  flags: number;
  upheld: number;
  overruled: number;
  dismissed: number;
  decisions: number;
  agreement: number | null;
  wilson_lower: number | null;
  status: "ready" | "advisory" | "too_few" | "blocks";
  unclear: boolean;
};
export type OriginRow = { origin: string; authors: number; versions: number; findings: number; blocking: number };
export type HealthResponse = {
  scope: "org" | "mine";
  synthetic: boolean;
  unclear: number;
  min_decisions: number;
  rules: HealthRow[];
  by_origin: OriginRow[] | null;
};

export function guidelineHealth(onWaking: (w: boolean) => void = () => {}) {
  return request<HealthResponse>("/v1/health", {}, onWaking);
}
