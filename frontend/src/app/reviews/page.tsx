"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { PageHeader, Card, Button, VentureSelector, Spinner, EmptyState, Badge, Input } from "@/components/ui";
import { statusVariant } from "@/components/ui/badge";

export default function ReviewsPage() {
  const [selectedVenture, setSelectedVenture] = useState("");
  const [queue, setQueue] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [deciding, setDeciding] = useState<string | null>(null);
  const [notes, setNotes] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  useEffect(() => {
    if (selectedVenture) {
      loadQueue();
    }
  }, [selectedVenture]);

  async function loadQueue() {
    setLoading(true);
    try {
      const data = await api.reviews.queue(selectedVenture);
      setQueue(data);
      setError("");
    } catch (e: any) {
      setError(e.message || "Failed to load review queue");
      setQueue(null);
    } finally {
      setLoading(false);
    }
  }

  async function handleDecision(reviewId: string, decision: string) {
    setDeciding(reviewId);
    try {
      await api.reviews.decide(selectedVenture, {
        review_id: reviewId,
        decision,
        notes: notes || undefined,
      });
      setSuccessMessage(`Review ${decision === "approve" ? "approved" : "rejected"} successfully!`);
      setNotes("");
      setTimeout(() => setSuccessMessage(""), 3000);
      await loadQueue();
    } catch (e: any) {
      setError(e.message || "Failed to submit decision");
    } finally {
      setDeciding(null);
    }
  }

  const items = queue?.items || [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Reviews"
        actions={
          <div className="flex gap-3 items-center">
            <VentureSelector value={selectedVenture} onChange={setSelectedVenture} />
            {queue && (
              <div className="flex gap-2">
                <Badge variant="yellow">{queue.pending || 0} pending</Badge>
                <Badge variant="red">{queue.overdue || 0} overdue</Badge>
              </div>
            )}
          </div>
        }
      />

      {successMessage && (
        <div className="glass-card border-green-500/30 p-4 text-sm text-green-400">
          {successMessage}
        </div>
      )}

      {error && (
        <div className="glass-card border-red-500/30 p-4 text-sm text-red-400">
          {error}
        </div>
      )}

      {!selectedVenture ? (
        <EmptyState message="Select a venture to view pending reviews." />
      ) : loading ? (
        <Spinner text="Loading review queue..." />
      ) : items.length === 0 ? (
        <EmptyState
          message="No pending reviews"
          hint='Execute an agent with "Require approval" checked to create a review item.'
        />
      ) : (
        <div className="space-y-4">
          {items.map((item: any) => (
            <Card key={item.id} padding="lg">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <Badge variant={statusVariant(item.priority || "medium")}>
                      {item.priority}
                    </Badge>
                    <span className="text-xs text-[var(--text-muted)]">{item.item_type}</span>
                    <span className="text-xs text-[var(--text-muted)]">
                      {new Date(item.created_at).toLocaleString()}
                    </span>
                  </div>

                  {/* Content preview */}
                  <div className="code-block rounded p-3 mb-3 max-h-40 overflow-y-auto">
                    <pre className="text-xs text-[var(--text-secondary)] whitespace-pre-wrap">
                      {typeof item.content === "string"
                        ? item.content
                        : JSON.stringify(item.content, null, 2)}
                    </pre>
                  </div>

                  {/* Context */}
                  {item.context && Object.keys(item.context).length > 0 && (
                    <div className="text-xs text-[var(--text-muted)] mb-3">
                      <span className="font-medium">Context:</span>{" "}
                      {JSON.stringify(item.context)}
                    </div>
                  )}

                  {/* Notes input */}
                  <div className="mb-3">
                    <input
                      type="text"
                      placeholder="Add notes (optional)..."
                      value={deciding === item.id ? notes : ""}
                      onChange={(e) => { setDeciding(item.id); setNotes(e.target.value); }}
                      className="input-dark w-full"
                    />
                  </div>
                </div>
              </div>

              {/* Action buttons */}
              <div className="flex gap-2">
                <Button
                  onClick={() => handleDecision(item.id, "approve")}
                  disabled={deciding === item.id}
                  size="sm"
                  className="!from-green-600 !to-emerald-700"
                >
                  {deciding === item.id ? "..." : "Approve"}
                </Button>
                <Button
                  variant="danger"
                  onClick={() => handleDecision(item.id, "reject")}
                  disabled={deciding === item.id}
                  size="sm"
                >
                  Reject
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
