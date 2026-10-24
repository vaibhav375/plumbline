export type IntentValue = { key_phrases: string; cta: string; channel: string };

export function IntentForm({ value, onChange }: { value: IntentValue; onChange: (v: IntentValue) => void }) {
  return (
    <details className="group rounded-xl border border-line bg-panel px-4 py-3 text-sm">
      <summary className="cursor-pointer font-label text-xs font-semibold uppercase text-bone/80 marker:text-ash hover:text-bone">Optional: words and the call to action this post must keep</summary>
      <div className="mt-3 grid gap-3 text-bone/80 sm:grid-cols-3">
        <label>
          Key phrases, comma separated
          <input className="mt-1 w-full rounded-md border border-line bg-carbon px-2.5 py-1.5 text-bone placeholder:text-ash focus:border-iris focus:outline-none" value={value.key_phrases}
            onChange={(e) => onChange({ ...value, key_phrases: e.target.value })} placeholder="dark spots" />
        </label>
        <label>
          Call to action
          <input className="mt-1 w-full rounded-md border border-line bg-carbon px-2.5 py-1.5 text-bone placeholder:text-ash focus:border-iris focus:outline-none" value={value.cta}
            onChange={(e) => onChange({ ...value, cta: e.target.value })} placeholder="Shop" />
        </label>
        <label>
          Channel
          <select className="mt-1 w-full rounded-md border border-line bg-carbon px-2.5 py-1.5 text-bone placeholder:text-ash focus:border-iris focus:outline-none" value={value.channel}
            onChange={(e) => onChange({ ...value, channel: e.target.value })}>
            {["instagram", "email", "web", "print", "other"].map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>
      </div>
    </details>
  );
}
