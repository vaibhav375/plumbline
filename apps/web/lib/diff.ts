export type DiffPart = { kind: "same" | "add" | "del"; text: string };

/** Word-level diff (longest common subsequence). Posts are short, so O(n·m) is fine. */
export function wordDiff(before: string, after: string): DiffPart[] {
  const a = before.split(/(\s+)/);
  const b = after.split(/(\s+)/);
  const dp = Array.from({ length: a.length + 1 }, () => new Array<number>(b.length + 1).fill(0));
  for (let i = a.length - 1; i >= 0; i--)
    for (let j = b.length - 1; j >= 0; j--)
      dp[i][j] = a[i] === b[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
  const out: DiffPart[] = [];
  const push = (kind: DiffPart["kind"], text: string) => {
    const last = out[out.length - 1];
    if (last && last.kind === kind) last.text += text;
    else out.push({ kind, text });
  };
  let i = 0;
  let j = 0;
  while (i < a.length && j < b.length) {
    if (a[i] === b[j]) {
      push("same", a[i]);
      i++;
      j++;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      push("del", a[i++]);
    } else {
      push("add", b[j++]);
    }
  }
  while (i < a.length) push("del", a[i++]);
  while (j < b.length) push("add", b[j++]);
  return group(out);
}

/** Changes separated only by spaces read as one swap: all of it deleted, then all of it inserted. */
function group(parts: DiffPart[]): DiffPart[] {
  const out: DiffPart[] = [];
  let del = "";
  let add = "";
  const flush = () => {
    if (del) out.push({ kind: "del", text: del.trimEnd() });
    if (add) out.push({ kind: "add", text: add.trimEnd() });
    const tail = (add || del).match(/\s+$/)?.[0];
    if (tail) out.push({ kind: "same", text: tail });
    del = "";
    add = "";
  };
  for (let k = 0; k < parts.length; k++) {
    const p = parts[k];
    const between = p.kind === "same" && !p.text.trim() && (del || add) && parts[k + 1] && parts[k + 1].kind !== "same";
    if (p.kind === "del") del += p.text;
    else if (p.kind === "add") add += p.text;
    else if (between) {
      del += del ? p.text : "";
      add += add ? p.text : "";
    } else {
      flush();
      out.push(p);
    }
  }
  flush();
  return out;
}
