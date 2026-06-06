"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { PageHeader, Card, Button, Badge, Spinner } from "@/components/ui";
import { statusVariant } from "@/components/ui/badge";
import { api, apiFetch } from "@/lib/api";

interface IntelligenceItem {
  id: string;
  agent_id: string;
  agent_name: string;
  task: string;
  output: string;
  cost_usd: number;
  trace_id: string | null;
  created_at: string;
  rating?: number;
}

interface NextAction {
  recommendation: string;
  context_used: string;
}

interface Venture {
  id: string;
  name: string;
  domain: string;
  stage?: string;
}

const LIFECYCLE_STAGES = [
  { name: "thesis", label: "Thesis" },
  { name: "discovery", label: "Discovery" },
  { name: "market", label: "Market" },
  { name: "offer", label: "Offer" },
  { name: "blueprint", label: "Blueprint" },
  { name: "agents", label: "Agents" },
];

export default function VentureCommandCenter() {
  const params = useParams();
  const router = useRouter();
  const ventureId = params.id as string;

  const [venture, setVenture] = useState<Venture | null>(null);
  const [intelligence, setIntelligence] = useState<IntelligenceItem[]>([]);
  const [nextAction, setNextAction] = useState<NextAction | null>(null);
  const [loadingVenture, setLoadingVenture] = useState(true);
  const [loadingIntel, setLoadingIntel] = useState(true);
  const [loadingAction, setLoadingAction] = useState(false);
  const [runningNetwork, setRunningNetwork] = useState(false);
  const [ratings, setRatings] = useState<Record<string, number>>({});
  const [ratingSubmitting, setRatingSubmitting] = useState<string | null>(null);

  useEffect(() => {
    if (!ventureId) return;
    loadVenture();
    loadIntelligence();
  }, [ventureId]);

  async function loadVenture() {
    try {
      const v = await api.ventures.get(ventureId);
      setVenture(v);
    } catch {
      setVenture(null);
    } finally {
      setLoadingVenture(false);
    }
  }

  async function loadIntelligence() {
    try {
      const items = await api.agents.intelligence(ventureId);
      setIntelligence(items);
    } catch {
      setIntelligence([]);
    } finally {
      setLoadingIntel(false);
    }
  }

  async function fetchNextAction() {
    setLoadingAction(true);
    try {
      const result = await api.agents.nextAction(ventureId);
      setNextAction(result);
    } catch (err: any) {
      setNextAction({ recommendation: "Unable to generate recommendation: " + err.message, context_used: "" });
    } finally {
      setLoadingAction(false);
    }
  }

  async function handleRunNetwork() {
    setRunningNetwork(true);
    try {
      await api.agents.runNetwork(ventureId);
      // Reload intelligence after network run
      await loadIntelligence();
    } catch (err: any) {
      alert("Network run failed: " + err.message);
    } finally {
      setRunningNetwork(false);
    }
  }

  async function handleRating(item: IntelligenceItem, rating: number) {
    setRatingSubmitting(item.id);
    try {
      await api.agents.submitFeedback({
        venture_id: ventureId,
        execution_id: item.id,
        agent_id: item.agent_id,
        rating,
      });
      setRatings((prev) => ({ ...prev, [item.id]: rating }));
    } catch (err: any) {
      // Silently fail for now
    } finally {
      setRatingSubmitting(null);
    }
  }

  if (loadingVenture) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Spinner text="Loading venture..." />
      </div>
    );
  }

  if (!venture) {
    return (
      <div className="space-y-6">
        <PageHeader title="Venture Not Found" subtitle="The requested venture could not be loaded." />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={venture.name}
        subtitle={`Domain: ${venture.domain} — Venture Command Center`}
        actions={
          <div className="flex gap-3">
            <Badge variant="purple">{venture.stage || "active"}</Badge>
          </div>
        }
      />

      {/* Lifecycle Progress */}
      <Card padding="lg">
        <h2 className="text-sm font-semibold text-[var(--text-primary)] mb-4">Lifecycle Progress</h2>
        <div className="relative">
          <div className="absolute top-4 left-6 right-6 h-0.5 bg-[var(--border-subtle)]" />
          <div className="relative grid grid-cols-6 gap-2">
            {LIFECYCLE_STAGES.map((stage) => {
              const isActive = venture.stage === stage.name;
              const isPast = false; // Could be computed from workflow status
              return (
                <div key={stage.name} className="flex flex-col items-center text-center">
                  <div className={`relative z-10 w-8 h-8 rounded-full flex items-center justify-center border-2 transition-all ${
                    isActive
                      ? "bg-violet-500/20 border-violet-500 shadow-[0_0_12px_rgba(139,92,246,0.4)]"
                      : "bg-[var(--bg-card)] border-[var(--border-subtle)]"
                  }`}>
                    {isActive ? (
                      <div className="w-3 h-3 bg-violet-400 rounded-full animate-pulse" />
                    ) : (
                      <div className="w-2 h-2 bg-[var(--text-muted)] rounded-full" />
                    )}
                  </div>
                  <p className={`mt-2 text-xs font-medium ${
                    isActive ? "text-violet-300" : "text-[var(--text-muted)]"
                  }`}>
                    {stage.label}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </Card>

      {/* AI Next Action */}
      <Card padding="lg" className="!border-violet-500/20 bg-gradient-to-br from-violet-950/30 to-transparent">
        <div className="flex items-start justify-between mb-3">
          <div>
            <h2 className="text-sm font-semibold text-violet-300">AI Next Action</h2>
            <p className="text-xs text-[var(--text-muted)] mt-0.5">AI-powered recommendation for your next step</p>
          </div>
          <Button size="sm" onClick={fetchNextAction} disabled={loadingAction}>
            {loadingAction ? "Thinking..." : "Get Recommendation"}
          </Button>
        </div>
        {nextAction ? (
          <div className="mt-3 p-4 rounded-lg bg-[var(--bg-card)] border border-[var(--border-subtle)]">
            <p className="text-sm text-[var(--text-primary)] leading-relaxed">{nextAction.recommendation}</p>
          </div>
        ) : (
          <p className="text-sm text-[var(--text-muted)] mt-3">
            Click &ldquo;Get Recommendation&rdquo; to receive an AI-powered suggestion based on your venture state.
          </p>
        )}
      </Card>

      {/* Quick Actions */}
      <div className="grid grid-cols-3 gap-4">
        <Card padding="md" className="text-center">
          <h3 className="text-xs font-semibold text-[var(--text-secondary)] mb-3">Agent Network</h3>
          <Button onClick={handleRunNetwork} disabled={runningNetwork} className="w-full">
            {runningNetwork ? "Running..." : "Run Network"}
          </Button>
        </Card>
        <Card padding="md" className="text-center">
          <h3 className="text-xs font-semibold text-[var(--text-secondary)] mb-3">Lifecycle Pipeline</h3>
          <Button variant="ghost" onClick={() => router.push("/lifecycle")} className="w-full">
            Launch Lifecycle
          </Button>
        </Card>
        <Card padding="md" className="text-center">
          <h3 className="text-xs font-semibold text-[var(--text-secondary)] mb-3">Market Analysis</h3>
          <Button variant="ghost" onClick={() => router.push("/market")} className="w-full">
            Analyze Market
          </Button>
        </Card>
      </div>

      {/* Intelligence Feed */}
      <Card padding="lg">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-[var(--text-primary)]">Intelligence Feed</h2>
          <Badge variant="purple">{intelligence.length} entries</Badge>
        </div>
        {loadingIntel ? (
          <Spinner text="Loading intelligence..." />
        ) : intelligence.length === 0 ? (
          <p className="text-sm text-[var(--text-muted)] text-center py-8">
            No intelligence gathered yet. Run your agent network to start building the knowledge base.
          </p>
        ) : (
          <div className="space-y-3 max-h-[500px] overflow-y-auto">
            {intelligence.map((item) => {
              const currentRating = ratings[item.id] || item.rating;
              return (
                <div
                  key={item.id}
                  className="relative pl-6 pb-3 border-l-2 border-[var(--border-subtle)] last:border-l-0"
                >
                  {/* Timeline dot */}
                  <div className="absolute left-[-5px] top-1 w-2 h-2 rounded-full bg-violet-500" />

                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <Badge variant="blue">{item.agent_name}</Badge>
                        {item.cost_usd > 0 && (
                          <span className="text-[10px] text-[var(--text-muted)]">
                            ${item.cost_usd.toFixed(4)}
                          </span>
                        )}
                        {currentRating && (
                          <span className="text-[10px] text-amber-400 flex items-center gap-0.5">
                            {"★".repeat(currentRating)}{"☆".repeat(5 - currentRating)}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-[var(--text-secondary)] mb-1 truncate">
                        Task: {item.task}
                      </p>
                      <p className="text-xs text-[var(--text-muted)] line-clamp-3">
                        {item.output}
                      </p>
                      {/* Rating buttons */}
                      <div className="flex items-center gap-1 mt-2">
                        <span className="text-[10px] text-[var(--text-muted)] mr-1">Rate:</span>
                        <button
                          onClick={() => handleRating(item, 5)}
                          disabled={ratingSubmitting === item.id}
                          className={`p-1 rounded transition-colors ${
                            currentRating && currentRating >= 4
                              ? "text-green-400"
                              : "text-[var(--text-muted)] hover:text-green-400"
                          }`}
                          title="Thumbs up (5)"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M7 10v12" /><path d="M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2h0a3.13 3.13 0 0 1 3 3.88Z" />
                          </svg>
                        </button>
                        <button
                          onClick={() => handleRating(item, 1)}
                          disabled={ratingSubmitting === item.id}
                          className={`p-1 rounded transition-colors ${
                            currentRating && currentRating <= 2
                              ? "text-red-400"
                              : "text-[var(--text-muted)] hover:text-red-400"
                          }`}
                          title="Thumbs down (1)"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M17 14V2" /><path d="M9 18.12 10 14H4.17a2 2 0 0 1-1.92-2.56l2.33-8A2 2 0 0 1 6.5 2H20a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2.76a2 2 0 0 0-1.79 1.11L12 22h0a3.13 3.13 0 0 1-3-3.88Z" />
                          </svg>
                        </button>
                        {ratingSubmitting === item.id && (
                          <span className="text-[10px] text-[var(--text-muted)] ml-1">saving...</span>
                        )}
                      </div>
                    </div>
                    <span className="text-[10px] text-[var(--text-muted)] whitespace-nowrap ml-3">
                      {new Date(item.created_at).toLocaleString()}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </Card>
    </div>
  );
}
