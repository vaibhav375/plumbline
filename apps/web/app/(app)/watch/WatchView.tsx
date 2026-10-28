"use client";

import { Eye, Globe, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { WakingBanner } from "@/components/WakingBanner";
import { CheckError, type WatchOverview, type WatchTask, type WatchUrl, watchApi } from "@/lib/api";

const REASON: Record<WatchTask["reason"], { label: string; tone: string }> = {
  removed: { label: "Fact withdrawn", tone: "border-blocking/60 text-blocking" },
  expired: { label: "Fact expired", tone: "border-blocking/60 text-blocking" },
  unverified: { label: "Fact unverified", tone: "border-major/60 text-major" },
  changed: { label: "Fact changed", tone: "border-major/60 text-major" },
  drift: { label: "Page changed", tone: "border-iris/60 text-iris" },
};
const when = (at: string) =>
  new Date(at).toLocaleString("en-IN", { timeZone: "Asia/Kolkata", dateStyle: "medium", timeStyle: "short" });
const card = "rounded-2xl border border-line bg-panel p-5 sm:p-6";
const field = "w-full rounded-md border border-line bg-carbon px-2.5 py-1.5 text-bone placeholder:text-ash focus:border-iris focus:outline-none";

function Result({ r }: { r: NonNullable<WatchUrl["last_result"]> }) {
  if (r.status === "ok") return <span className="text-ok">Matches the approved text ({r.checked} sentences)</span>;
  if (r.status === "unreachable") return <span className="text-major">Couldn&apos;t read it: {r.error}</span>;
  return <span className="text-blocking">{r.missing?.length} approved sentence{r.missing?.length === 1 ? "" : "s"} missing or changed</span>;
}

function Task({ t, onDone, busy }: { t: WatchTask; onDone: (status: "done" | "dismissed", note?: string) => void; busy: boolean }) {
  const [dismissing, setDismissing] = useState(false);
  const [note, setNote] = useState("");
  return (
    <li className="rounded-xl border border-line bg-carbon/60 p-4">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className={`rounded border px-2 py-0.5 font-label text-[11px] uppercase ${REASON[t.reason].tone}`}>{REASON[t.reason].label}</span>
        <span className="font-semibold text-bone">{t.title}</span>
        {t.fact_id && <span className="font-mono text-ash">{t.fact_id}</span>}
        <span className="ml-auto text-ash">{t.owner_name ?? "Unassigned"} · {when(t.created_at)}</span>
      </div>
      <p className="mt-2 text-sm text-bone/90">{t.detail}</p>
      <p className="mt-2 text-sm text-bone/80">
        {t.replacement ? <>Say instead: <b className="text-ok">{t.replacement}</b></> : "No approved replacement exists: update it with compliance, or withdraw the post."}
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Button size="sm" disabled={busy} onClick={() => onDone("done", "Updated or withdrawn")}>Mark done</Button>
        {!dismissing && <Button size="sm" variant="ghost" disabled={busy} onClick={() => setDismissing(true)}>Dismiss</Button>}
      </div>
      {dismissing && (
        <form className="mt-3 flex flex-wrap items-end gap-2 text-sm" onSubmit={(e) => { e.preventDefault(); onDone("dismissed", note); }}>
          <label className="grow">Why dismiss it? (required)
            <input className={`mt-1 ${field}`} value={note} onChange={(e) => setNote(e.target.value)} />
          </label>
          <Button size="sm" type="submit" disabled={busy || !note.trim()}>Dismiss with reason</Button>
          <Button size="sm" type="button" variant="ghost" onClick={() => setDismissing(false)}>Cancel</Button>
        </form>
      )}
    </li>
  );
}

export function WatchView() {
  const [data, setData] = useState<WatchOverview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [waking, setWaking] = useState(false);
  const [busy, setBusy] = useState(false);
  const [version, setVersion] = useState("");
  const [url, setUrl] = useState("");
  const [msg, setMsg] = useState<string | null>(null);

  const load = useCallback(() => {
    watchApi.overview(setWaking).then(setData, (e) => setError(e instanceof CheckError ? e.message : "Couldn't load this page."));
  }, []);
  useEffect(load, [load]);

  async function act(job: () => Promise<unknown>, done?: string) {
    setBusy(true);
    setError(null);
    setMsg(null);
    try {
      await job();
      if (done) setMsg(done);
      load();
    } catch (e) {
      setError(e instanceof CheckError ? e.message : "That didn't work. Try again.");
    } finally {
      setBusy(false);
    }
  }

  if (error && !data) return <p role="alert" className="rounded-xl border border-blocking/40 bg-blocking/[0.07] px-4 py-3 text-sm text-blocking">{error}</p>;
  if (!data) return <>{waking && <WakingBanner />}<p className="text-sm text-ash">Loading and scanning…</p></>;

  return (
    <div className="space-y-6">
      {error && <p role="alert" className="rounded-xl border border-blocking/40 bg-blocking/[0.07] px-4 py-3 text-sm text-blocking">{error}</p>}
      {msg && <p role="status" className="rounded-xl border border-ok/40 bg-ok/[0.07] px-4 py-3 text-sm text-ok">{msg}</p>}

      <section aria-labelledby="tasks" className={card}>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 id="tasks" className="flex items-center gap-2 text-lg"><Eye className="size-5 text-iris" aria-hidden />Update or withdraw</h2>
          {data.everyone && (
            <Button size="sm" variant="outline" disabled={busy}
              onClick={() => act(async () => { const r = await watchApi.scan(); setMsg(`Scanned ${r.posts} live post${r.posts === 1 ? "" : "s"}: ${r.new_tasks} new task${r.new_tasks === 1 ? "" : "s"}.`); })}>
              <RefreshCw aria-hidden /> Scan now
            </Button>
          )}
        </div>
        {data.scanned && (
          <p className="mt-2 text-sm text-ash">Just scanned {data.scanned.posts} live post{data.scanned.posts === 1 ? "" : "s"} (approved versions) against today&apos;s facts.</p>
        )}
        {data.tasks.length === 0 ? (
          <p className="mt-4 text-sm text-bone/80" data-testid="no-watch-tasks">
            Nothing needs updating. Every live post&apos;s facts are as they were when it was approved. Posts checked before the watch existed have no
            fact record: check them again to include them.
          </p>
        ) : (
          <ul className="mt-4 space-y-3" data-testid="watch-tasks">
            {data.tasks.map((t) => (
              <Task key={t.id} t={t} busy={busy} onDone={(status, note) => act(() => watchApi.resolve(t.id, status, note))} />
            ))}
          </ul>
        )}
        {data.closed.some((t) => t.status !== "open") && (
          <details className="mt-5 text-sm">
            <summary className="cursor-pointer font-label text-xs text-ash uppercase">Closed tasks</summary>
            <ul className="mt-2 divide-y divide-line rounded-lg border border-line">
              {data.closed.filter((t) => t.status !== "open").map((t) => (
                <li key={t.id} className="px-3 py-2 text-bone/80">
                  <b>{t.title}</b> · {REASON[t.reason].label} · {t.status}{t.note ? `: “${t.note}”` : ""} <span className="text-xs text-ash">{t.resolved_at && when(t.resolved_at)}</span>
                </li>
              ))}
            </ul>
          </details>
        )}
      </section>

      <section aria-labelledby="pages" className={card}>
        <h2 id="pages" className="flex items-center gap-2 text-lg"><Globe className="size-5 text-iris" aria-hidden />Live pages</h2>
        <p className="mt-2 max-w-3xl text-sm text-bone/80">
          Tell Plumbline where an approved post is live. It reads the page and compares it with the approved text, sentence by sentence; extra text on
          the page is ignored, but a missing or reworded sentence (or a changed number) raises a task.
        </p>
        <form className="mt-4 grid gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)_auto] sm:items-end"
          onSubmit={(e) => { e.preventDefault(); act(async () => { const r = await watchApi.register(version, url); setUrl(""); setMsg(r.status === "ok" ? "Registered. The page matches the approved text." : r.status === "drift" ? "Registered. The page already differs from the approved text: see the task above." : `Registered, but ${r.error ?? "the page couldn't be read"}.`); }); }}>
          <label className="text-sm"><span className="font-label text-xs text-ash uppercase">Approved post</span>
            <select className={`mt-1 ${field}`} value={version} onChange={(e) => setVersion(e.target.value)} required>
              <option value="">Choose…</option>
              {data.posts.map((p) => <option key={p.version_id} value={p.version_id}>{p.title.slice(0, 50)} (v{p.n})</option>)}
            </select>
          </label>
          <label className="text-sm"><span className="font-label text-xs text-ash uppercase">Live address</span>
            <input className={`mt-1 ${field}`} type="url" value={url} placeholder="https://shop.example.com/serum" required onChange={(e) => setUrl(e.target.value)} />
          </label>
          <Button type="submit" disabled={busy || !version || !url.trim()}>Register and read</Button>
        </form>
        {data.posts.length === 0 && <p className="mt-2 text-xs text-ash">No approved posts yet: a post appears here once it is approved.</p>}
        {data.urls.length > 0 && (
          <ul className="mt-4 divide-y divide-line rounded-lg border border-line">
            {data.urls.map((u) => (
              <li key={u.version_id} className="flex flex-wrap items-center justify-between gap-2 px-3 py-2 text-sm">
                <span className="min-w-0">
                  <b className="text-bone">{u.title.slice(0, 60)}</b> <span className="font-mono text-xs break-all text-iris">{u.url}</span>
                  <span className="block text-xs text-ash">
                    {u.last_result ? <><Result r={u.last_result} /> · checked {u.last_checked_at && when(u.last_checked_at)}</> : "Not read yet"}
                  </span>
                </span>
                <Button size="sm" variant="outline" disabled={busy} onClick={() => act(async () => { await watchApi.check(u.version_id); }, "Page read again.")}>Check now</Button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
