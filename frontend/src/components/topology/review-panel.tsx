"use client";

import { useCallback, useEffect, useState } from "react";
import {
  approveReview,
  fetchReview,
  type ReviewItem,
} from "@/lib/topology-api";

/**
 * The visible side of the Wizard-of-Oz human-in-the-loop (Step 5).
 *
 * Lists drafts parked in the human-review-queue (events tagged requires_human),
 * lets the founder edit the text and approve. Approving publishes
 * review.approved, which resumes the chain (post.approved → post-scheduler →
 * post.published) — the run then animates in the timeline via onApproved.
 */
export default function ReviewPanel({
  onApproved,
  refreshKey,
}: {
  onApproved: (correlationId: string) => void;
  refreshKey: number;
}) {
  const [pending, setPending] = useState<ReviewItem[]>([]);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setErr(null);
    try {
      const res = await fetchReview();
      setPending(res.pending);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }, []);

  // Reload whenever the parent signals a change (a run was triggered/approved).
  // The fetch is inlined with a cancellation guard so we only set state for the
  // latest in-flight request (and never synchronously within the effect body).
  useEffect(() => {
    let cancelled = false;
    fetchReview()
      .then((res) => {
        if (!cancelled) setPending(res.pending);
      })
      .catch((e: unknown) => {
        if (!cancelled) setErr(e instanceof Error ? e.message : String(e));
      });
    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  async function approve(item: ReviewItem) {
    setBusy(item.event_id);
    setErr(null);
    try {
      const draft = drafts[item.event_id] ?? defaultDraft(item);
      const res = await approveReview({
        event_id: item.event_id,
        venture_id: item.venture_id,
        draft,
      });
      await load();
      onApproved(res.correlation_id);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  }

  if (pending.length === 0) {
    return (
      <div className="border-b border-white/10 p-3">
        <h2 className="mb-1 text-sm font-semibold">
          Review queue{" "}
          <span className="font-normal text-slate-500">(human-in-the-loop)</span>
        </h2>
        <p className="text-xs text-slate-500">
          No drafts awaiting approval. Trigger{" "}
          <span className="text-emerald-300">Customer sends input</span> to create
          one.
        </p>
      </div>
    );
  }

  return (
    <div className="border-b border-white/10 p-3">
      <h2 className="mb-2 text-sm font-semibold">
        Review queue{" "}
        <span className="rounded bg-amber-500/20 px-1.5 text-[10px] font-semibold text-amber-200">
          {pending.length} pending
        </span>
      </h2>
      <div className="space-y-2">
        {pending.map((item) => (
          <div
            key={item.event_id}
            className="rounded-md border border-amber-400/30 bg-amber-500/5 p-2"
          >
            <div className="mb-1 flex items-center justify-between">
              <span className="font-mono text-[10px] text-slate-400">
                {String(item.payload.customer_id ?? "—")} · {item.type}
              </span>
              <span className="font-mono text-[10px] text-slate-500">
                {item.event_id.slice(0, 8)}
              </span>
            </div>
            <textarea
              value={drafts[item.event_id] ?? defaultDraft(item)}
              onChange={(e) =>
                setDrafts((d) => ({ ...d, [item.event_id]: e.target.value }))
              }
              rows={3}
              spellCheck={false}
              className="mb-1.5 w-full rounded-md border border-white/15 bg-black/30 px-2 py-1 text-[11px]"
            />
            <button
              onClick={() => approve(item)}
              disabled={busy !== null}
              className="w-full rounded-md border border-emerald-400/40 bg-emerald-500/10 px-2 py-1 text-xs font-medium text-emerald-100 hover:bg-emerald-500/20 disabled:opacity-50"
            >
              {busy === item.event_id ? "Approving…" : "✓ Approve & publish"}
            </button>
          </div>
        ))}
      </div>
      {err && <p className="mt-2 text-[11px] text-rose-400">{err}</p>}
    </div>
  );
}

// The founder edits from the placeholder draft the HumanDrafter produced.
function defaultDraft(item: ReviewItem): string {
  const d = item.payload.draft;
  return typeof d === "string" ? d : "";
}
