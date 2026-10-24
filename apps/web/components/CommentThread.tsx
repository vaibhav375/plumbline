"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import type { ReviewDetail } from "@/lib/api";

export function CommentThread({ comments, onAdd }: { comments: ReviewDetail["comments"]; onAdd: (body: string) => Promise<void> }) {
  const [body, setBody] = useState("");
  return (
    <section aria-labelledby="comments" className="rounded-xl bg-panel shadow-sm ring-1 ring-line p-4">
      <h2 id="comments" className="font-semibold">Comments</h2>
      <ul className="mt-2 space-y-2 text-sm">
        {comments.map((c, i) => <li key={i}><span className="font-medium">{c.who}</span>: {c.body}</li>)}
        {!comments.length && <li className="text-muted-foreground">No comments yet.</li>}
      </ul>
      <form className="mt-3 flex gap-2" onSubmit={async (e) => { e.preventDefault(); await onAdd(body); setBody(""); }}>
        <label className="grow text-sm">
          <span className="sr-only">Add a comment</span>
          <input className="w-full rounded border px-2 py-1" value={body} onChange={(e) => setBody(e.target.value)} placeholder="Add a comment" />
        </label>
        <Button size="sm" type="submit" disabled={!body.trim()}>Comment</Button>
      </form>
    </section>
  );
}
