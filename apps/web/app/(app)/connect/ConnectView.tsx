"use client";

import { Check, Copy, KeyRound, MessageSquare, ShieldCheck } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { WakingBanner } from "@/components/WakingBanner";
import { CheckError, type ConnectOverview, connectApi } from "@/lib/api";

const when = (at: string) =>
  new Date(at).toLocaleString("en-IN", { timeZone: "Asia/Kolkata", dateStyle: "medium", timeStyle: "short" });

function CopyButton({ text, label }: { text: string; label: string }) {
  const [done, setDone] = useState(false);
  return (
    <Button type="button" size="sm" variant="outline" aria-label={label}
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setDone(true);
          setTimeout(() => setDone(false), 1500);
        } catch {
          /* clipboard blocked: the value is still on screen */
        }
      }}>
      {done ? <Check aria-hidden /> : <Copy aria-hidden />} {done ? "Copied" : "Copy"}
    </Button>
  );
}

const card = "rounded-2xl border border-line bg-panel p-5 sm:p-6";
const field = "w-full rounded-md border border-line bg-carbon px-2.5 py-1.5 text-bone placeholder:text-ash focus:border-iris focus:outline-none";

export function ConnectView() {
  const [data, setData] = useState<ConnectOverview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [waking, setWaking] = useState(false);
  const [code, setCode] = useState<{ code: string; minutes: number } | null>(null);
  const [newKey, setNewKey] = useState<{ key: string; label: string } | null>(null);
  const [label, setLabel] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    connectApi.overview(setWaking).then(setData, (e) => setError(e instanceof CheckError ? e.message : "Couldn't load this page."));
  }, []);
  useEffect(load, [load]);

  async function act(job: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await job();
      load();
    } catch (e) {
      setError(e instanceof CheckError ? e.message : "That didn't work. Try again.");
    } finally {
      setBusy(false);
    }
  }

  if (error && !data) return <p role="alert" className="rounded-xl border border-blocking/40 bg-blocking/[0.07] px-4 py-3 text-sm text-blocking">{error}</p>;
  if (!data) return <>{waking && <WakingBanner />}<p className="text-sm text-ash">Loading…</p></>;

  const sampleKey = newKey?.key ?? "plk_YOUR_KEY";
  const curl = `curl -H "Authorization: Bearer ${sampleKey}" \\\n  "${data.api_base}/v1/gate/versions/VERSION_ID"`;

  return (
    <div className="space-y-6">
      {error && <p role="alert" className="rounded-xl border border-blocking/40 bg-blocking/[0.07] px-4 py-3 text-sm text-blocking">{error}</p>}

      <section aria-labelledby="chat" className={card}>
        <h2 id="chat" className="flex items-center gap-2 text-lg"><MessageSquare className="size-5 text-iris" aria-hidden />Check in chat, against your brand</h2>
        <ol className="mt-3 list-decimal space-y-1 pl-5 text-sm text-bone/80 marker:text-ash">
          <li>Create a link code here. It works once and lasts 15 minutes.</li>
          <li>In ASI:One, open the agent <b>Plumbline Brand Checker</b>{data.agent_address && <> (<span className="font-mono text-xs text-iris break-all">{data.agent_address}</span>)</>}.</li>
          <li>Send it: <span className="font-mono text-bone">link ABCD-2345</span> (your code). From then on it checks that person&apos;s posts against your rulebook and facts, as an agency writer.</li>
        </ol>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <Button type="button" disabled={busy} onClick={() => act(async () => setCode(await connectApi.makeCode()))}>Create a link code</Button>
          {code && (
            <div role="status" className="flex flex-wrap items-center gap-3 rounded-lg border border-ok/40 bg-ok/[0.07] px-4 py-2">
              <span className="font-display text-3xl tracking-[0.12em] text-ok">{code.code}</span>
              <CopyButton text={`link ${code.code}`} label="Copy the link message" />
              <span className="text-xs text-ash">Shown once. Expires in {code.minutes} minutes.</span>
            </div>
          )}
        </div>
        <h3 className="mt-6 font-label text-xs text-ash uppercase">Linked addresses</h3>
        {data.links.length === 0 ? (
          <p className="mt-2 text-sm text-ash">No one is linked yet.{data.open_codes > 0 && ` ${data.open_codes} code${data.open_codes === 1 ? " is" : "s are"} waiting to be used.`}</p>
        ) : (
          <ul className="mt-2 divide-y divide-line rounded-lg border border-line">
            {data.links.map((l) => (
              <li key={l.address} className="flex flex-wrap items-center justify-between gap-2 px-3 py-2">
                <span><span className="font-mono text-xs break-all text-bone">{l.address}</span> <span className="text-xs text-ash">linked {when(l.linked_at)}</span></span>
                <Button size="sm" variant="ghost" disabled={busy} onClick={() => act(() => connectApi.revokeLink(l.address))}>Unlink</Button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="gate" className={card}>
        <h2 id="gate" className="flex items-center gap-2 text-lg"><ShieldCheck className="size-5 text-iris" aria-hidden />Publish gate</h2>
        <p className="mt-3 max-w-3xl text-sm text-bone/80">
          A scheduling or CMS tool asks Plumbline before it posts. The answer is <b>go</b> only for an approved version with no open blocking
          finding; otherwise <b>not yet</b>, with the reasons. Send the SHA-256 of the text you are about to publish as <span className="font-mono">?text_sha256=</span>
          and the gate also checks it is exactly the approved text.
        </p>
        <pre className="mt-3 overflow-x-auto rounded-lg border border-line bg-carbon p-3 font-mono text-xs text-bone/90">{curl}</pre>

        <form className="mt-5 flex flex-wrap items-end gap-3" onSubmit={(e) => { e.preventDefault(); act(async () => { setNewKey(await connectApi.makeKey(label)); setLabel(""); }); }}>
          <label className="grow text-sm sm:max-w-xs">
            <span className="font-label text-xs text-ash uppercase">Name the tool</span>
            <input className={`mt-1 ${field}`} value={label} maxLength={60} placeholder="e.g. Buffer scheduler" onChange={(e) => setLabel(e.target.value)} />
          </label>
          <Button type="submit" disabled={busy || !label.trim()}><KeyRound aria-hidden /> Create a gate key</Button>
        </form>
        {newKey && (
          <div role="status" className="mt-3 flex flex-wrap items-center gap-3 rounded-lg border border-ok/40 bg-ok/[0.07] px-4 py-2">
            <span className="font-mono text-sm break-all text-ok">{newKey.key}</span>
            <CopyButton text={newKey.key} label="Copy the gate key" />
            <span className="text-xs text-ash">Shown once. Store it in {newKey.label}.</span>
          </div>
        )}
        <h3 className="mt-6 font-label text-xs text-ash uppercase">Gate keys</h3>
        {data.keys.length === 0 ? (
          <p className="mt-2 text-sm text-ash">No keys yet.</p>
        ) : (
          <ul className="mt-2 divide-y divide-line rounded-lg border border-line">
            {data.keys.map((k) => (
              <li key={k.id} className="flex flex-wrap items-center justify-between gap-2 px-3 py-2 text-sm">
                <span className={k.revoked_at ? "text-ash line-through" : "text-bone"}>
                  {k.label} <span className="text-xs text-ash">· created {when(k.created_at)} · {k.last_used_at ? `last used ${when(k.last_used_at)}` : "never used"}</span>
                </span>
                {k.revoked_at ? <span className="font-label text-xs text-ash uppercase">Revoked</span>
                  : <Button size="sm" variant="ghost" disabled={busy} onClick={() => act(() => connectApi.revokeKey(k.id))}>Revoke</Button>}
              </li>
            ))}
          </ul>
        )}

        <h3 className="mt-6 font-label text-xs text-ash uppercase">What tools asked, and what they were told</h3>
        {data.calls.length === 0 ? (
          <p className="mt-2 text-sm text-ash">No questions yet.</p>
        ) : (
          <div className="mt-2 overflow-x-auto rounded-lg border border-line">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-line font-label text-[11px] text-ash uppercase">
                <tr><th scope="col" className="px-3 py-2">When (IST)</th><th scope="col" className="px-3 py-2">Answer</th><th scope="col" className="px-3 py-2">Reasons</th></tr>
              </thead>
              <tbody>
                {data.calls.map((c, i) => (
                  <tr key={i} className="border-t border-line align-top">
                    <td className="whitespace-nowrap px-3 py-2">{when(c.at)}</td>
                    <td className="px-3 py-2"><span className={`font-label text-xs uppercase ${c.decision === "go" ? "text-ok" : "text-blocking"}`}>{c.decision === "go" ? "Go" : "Not yet"}</span></td>
                    <td className="px-3 py-2 text-bone/80">{c.reasons.join(" ") || "Approved, nothing open."}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
