"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function ReviewsPage() {
  const [ventures, setVentures] = useState<any[]>([]);
  const [selectedVenture, setSelectedVenture] = useState("");
  const [queue, setQueue] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [deciding, setDeciding] = useState<string | null>(null);
  const [notes, setNotes] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  useEffect(() => {
    api.ventures.list().then(setVentures).catch(() => {});
  }, []);

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
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Reviews</h1>
        {queue && (
          <div className="flex gap-3 text-sm">
            <span className="px-3 py-1 bg-yellow-100 text-yellow-800 rounded-full font-medium">
              {queue.pending || 0} pending
            </span>
            <span className="px-3 py-1 bg-red-100 text-red-800 rounded-full font-medium">
              {queue.overdue || 0} overdue
            </span>
          </div>
        )}
      </div>

      {/* Venture Selector */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-1">Select Venture</label>
        <select
          value={selectedVenture}
          onChange={(e) => setSelectedVenture(e.target.value)}
          className="w-full max-w-xs px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">-- Select a venture --</option>
          {ventures.map((v) => (
            <option key={v.id} value={v.id}>{v.name}</option>
          ))}
        </select>
      </div>

      {successMessage && (
        <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-md mb-4 text-sm">
          {successMessage}
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md mb-4 text-sm">
          {error}
        </div>
      )}

      {!selectedVenture ? (
        <p className="text-gray-500">Select a venture to view pending reviews.</p>
      ) : loading ? (
        <p className="text-gray-500">Loading review queue...</p>
      ) : items.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-8 text-center">
          <p className="text-gray-500 text-lg">No pending reviews</p>
          <p className="text-gray-400 text-sm mt-2">
            Execute an agent with &quot;Require approval&quot; checked to create a review item.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {items.map((item: any) => (
            <div key={item.id} className="bg-white rounded-lg shadow p-6">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                      item.priority === "critical" ? "bg-red-100 text-red-800" :
                      item.priority === "high" ? "bg-orange-100 text-orange-800" :
                      item.priority === "medium" ? "bg-yellow-100 text-yellow-800" :
                      "bg-gray-100 text-gray-800"
                    }`}>
                      {item.priority}
                    </span>
                    <span className="text-xs text-gray-500">{item.item_type}</span>
                    <span className="text-xs text-gray-400">
                      {new Date(item.created_at).toLocaleString()}
                    </span>
                  </div>

                  {/* Content preview */}
                  <div className="bg-gray-50 rounded p-3 mb-3 max-h-40 overflow-y-auto">
                    <pre className="text-xs text-gray-700 whitespace-pre-wrap">
                      {typeof item.content === "string"
                        ? item.content
                        : JSON.stringify(item.content, null, 2)}
                    </pre>
                  </div>

                  {/* Context */}
                  {item.context && Object.keys(item.context).length > 0 && (
                    <div className="text-xs text-gray-500 mb-3">
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
                      className="w-full px-3 py-1.5 border border-gray-200 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>
              </div>

              {/* Action buttons */}
              <div className="flex gap-2">
                <button
                  onClick={() => handleDecision(item.id, "approve")}
                  disabled={deciding === item.id}
                  className="px-4 py-2 bg-green-600 text-white rounded-md text-sm font-medium hover:bg-green-700 disabled:opacity-50"
                >
                  {deciding === item.id ? "..." : "Approve"}
                </button>
                <button
                  onClick={() => handleDecision(item.id, "reject")}
                  disabled={deciding === item.id}
                  className="px-4 py-2 bg-red-600 text-white rounded-md text-sm font-medium hover:bg-red-700 disabled:opacity-50"
                >
                  Reject
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
