"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import type { ReviewDetail } from "@/lib/api";

export function CommentThread({ comments, onAdd }: { comments: ReviewDetail["comments"]; onAdd: (body: string) => Promise<void> }) {
  const [body, setBody] = useState("");
  return (
    <section aria-labelledby="comments" className="rounded-xl border border-line bg-panel p-5">
      <h2 id="comments" className="text-base">Comments</h2>
      <ul className="mt-3 space-y-2 text-sm">
        {comments.map((c, i) => (
          <li key={i} className="rounded-lg bg-raised px-3 py-2">
            <span className="block font-label text-[11px] font-semibold uppercase text-iris">{c.who}</span>{c.body}
          </li>
        ))}
        {!comments.length && <li className="text-muted-foreground">No comments yet.</li>}
      </ul>
      <form className="mt-3 flex gap-2" onSubmit={async (e) => { e.preventDefault(); await onAdd(body); setBody(""); }}>
        <label className="grow text-sm">
          <span className="sr-only">Add a comment</span>
          <input className="w-full rounded-md border border-line bg-carbon px-2.5 py-1.5 text-bone placeholder:text-ash focus:border-iris focus:outline-none" value={body} onChange={(e) => setBody(e.target.value)} placeholder="Add a comment" />
        </label>
        <Button size="sm" type="submit" disabled={!body.trim()}>Comment</Button>
      </form>
    </section>
  );
}
