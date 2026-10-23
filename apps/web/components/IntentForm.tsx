export type IntentValue = { key_phrases: string; cta: string; channel: string };

export function IntentForm({ value, onChange }: { value: IntentValue; onChange: (v: IntentValue) => void }) {
  return (
    <details className="rounded-md border p-3 text-sm">
      <summary className="cursor-pointer">Optional: words and the call to action this post must keep</summary>
      <div className="mt-3 grid gap-3 sm:grid-cols-3">
        <label>
          Key phrases, comma separated
          <input className="mt-1 w-full rounded border px-2 py-1" value={value.key_phrases}
            onChange={(e) => onChange({ ...value, key_phrases: e.target.value })} placeholder="dark spots" />
        </label>
        <label>
          Call to action
          <input className="mt-1 w-full rounded border px-2 py-1" value={value.cta}
            onChange={(e) => onChange({ ...value, cta: e.target.value })} placeholder="Shop" />
        </label>
        <label>
          Channel
          <select className="mt-1 w-full rounded border px-2 py-1" value={value.channel}
            onChange={(e) => onChange({ ...value, channel: e.target.value })}>
            {["instagram", "email", "web", "print", "other"].map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>
      </div>
    </details>
  );
}
