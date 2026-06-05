"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { PageHeader, Card, Button, Modal, VentureSelector, Spinner, EmptyState, Badge, Input, Textarea } from "@/components/ui";
import { statusVariant } from "@/components/ui/badge";
import { ConfidenceBar } from "@/components/ui";

interface MarketSignal {
  id: string;
  signal_type: string;
  title: string;
  summary: string;
  relevance_score: number;
  impact_score: number;
  tags: string[];
  detected_at: string;
}

export default function MarketIntelPage() {
  const [selectedVenture, setSelectedVenture] = useState("");
  const [signals, setSignals] = useState<MarketSignal[]>([]);
  const [loading, setLoading] = useState(false);

  // Analyze form
  const [showAnalyze, setShowAnalyze] = useState(false);
  const [analyzeText, setAnalyzeText] = useState("");
  const [analyzeDomain, setAnalyzeDomain] = useState("");
  const [analyzeFocus, setAnalyzeFocus] = useState("");
  const [analysisResult, setAnalysisResult] = useState<any>(null);

  // Report
  const [showReport, setShowReport] = useState(false);
  const [report, setReport] = useState<any>(null);
  const [reportLoading, setReportLoading] = useState(false);

  // Opportunity Score
  const [showScore, setShowScore] = useState(false);
  const [oppDescription, setOppDescription] = useState("");
  const [oppDomain, setOppDomain] = useState("");
  const [oppScore, setOppScore] = useState<any>(null);

  useEffect(() => {
    if (selectedVenture) {
      setLoading(true);
      api.market
        .getSignals(selectedVenture)
        .then(setSignals)
        .catch(() => setSignals([]))
        .finally(() => setLoading(false));
    }
  }, [selectedVenture]);

  async function handleAnalyze() {
    if (!selectedVenture || !analyzeText || !analyzeDomain) return;
    setLoading(true);
    try {
      const result = await api.market.analyzeSignals(selectedVenture, {
        venture_id: selectedVenture,
        domain: analyzeDomain,
        signals_text: analyzeText,
        focus_areas: analyzeFocus.split(",").map((s) => s.trim()).filter(Boolean),
      });
      setAnalysisResult(result);
      // Refresh signals
      const updated = await api.market.getSignals(selectedVenture);
      setSignals(updated);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleGenerateReport() {
    if (!selectedVenture) return;
    setReportLoading(true);
    try {
      const result = await api.market.generateReport(selectedVenture, {
        venture_id: selectedVenture,
        domain: analyzeDomain || "general",
        report_type: "digest",
        period: "weekly",
      });
      setReport(result);
      setShowReport(true);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setReportLoading(false);
    }
  }

  async function handleScoreOpportunity() {
    if (!selectedVenture || !oppDescription || !oppDomain) return;
    try {
      const result = await api.market.scoreOpportunity(selectedVenture, oppDescription, oppDomain);
      setOppScore(result);
    } catch (err: any) {
      alert(err.message);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Market & Signal Intelligence"
        subtitle="Monitor competitors, detect trends, score opportunities. Evidence over gut feel."
        actions={
          <div className="flex gap-3 items-center">
            <VentureSelector value={selectedVenture} onChange={setSelectedVenture} />
            {selectedVenture && (
              <>
                <Button onClick={() => setShowAnalyze(true)}>Analyze Signals</Button>
                <Button variant="ghost" onClick={handleGenerateReport} disabled={reportLoading}>
                  {reportLoading ? "Generating..." : "Generate Report"}
                </Button>
                <Button variant="ghost" onClick={() => setShowScore(true)}>
                  Score Opportunity
                </Button>
              </>
            )}
          </div>
        }
      />

      {/* Signals Grid */}
      {selectedVenture && (
        <div className="space-y-4">
          {loading ? (
            <Spinner text="Loading signals..." />
          ) : signals.length === 0 ? (
            <EmptyState
              message="No market signals detected yet."
              hint="Paste market research, news articles, or competitor data to analyze."
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {signals.map((signal) => (
                <Card key={signal.id}>
                  <div className="flex items-start justify-between">
                    <h3 className="font-medium text-[var(--text-primary)] text-sm">{signal.title}</h3>
                    <Badge variant={statusVariant(signal.signal_type)}>
                      {signal.signal_type}
                    </Badge>
                  </div>
                  <p className="text-sm text-[var(--text-secondary)] mt-2">{signal.summary}</p>
                  <div className="flex items-center gap-4 mt-3">
                    <div className="flex-1">
                      <ConfidenceBar value={signal.relevance_score} height="sm" showLabel label="Relevance" />
                    </div>
                    <div className="flex-1">
                      <ConfidenceBar value={signal.impact_score} height="sm" showLabel label="Impact" />
                    </div>
                  </div>
                  {signal.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {signal.tags.map((tag, i) => (
                        <span key={i} className="text-xs bg-[var(--bg-secondary)] text-[var(--text-muted)] px-2 py-0.5 rounded border border-[var(--border-subtle)]">
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Analysis Result */}
      {analysisResult && (
        <Card className="border-[var(--accent-purple)]/30">
          <h3 className="text-sm font-semibold text-[var(--accent-purple)] mb-2">Analysis Result</h3>
          <p className="text-sm text-[var(--text-secondary)]">{analysisResult.summary}</p>
          {analysisResult.patterns?.length > 0 && (
            <div className="mt-3">
              <h4 className="text-xs font-medium text-[var(--text-muted)] mb-1">Patterns Detected:</h4>
              <ul className="list-disc list-inside text-sm text-[var(--text-secondary)]">
                {analysisResult.patterns.map((p: string, i: number) => (
                  <li key={i}>{p}</li>
                ))}
              </ul>
            </div>
          )}
        </Card>
      )}

      {/* Report Modal */}
      <Modal open={showReport && !!report} onClose={() => setShowReport(false)} title="Market Intelligence Report" wide>
        {report && (
          <div className="space-y-4 max-h-[60vh] overflow-y-auto">
            <p className="whitespace-pre-wrap text-sm text-[var(--text-secondary)]">{report.content}</p>
            {report.key_findings?.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-2">Key Findings</h3>
                <ul className="space-y-1">
                  {report.key_findings.map((f: string, i: number) => (
                    <li key={i} className="text-sm text-[var(--text-secondary)] flex items-start gap-2">
                      <span className="text-green-400 mt-0.5">+</span> {f}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {report.recommendations?.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-2">Recommendations</h3>
                <ul className="space-y-1">
                  {report.recommendations.map((r: string, i: number) => (
                    <li key={i} className="text-sm text-[var(--text-secondary)] flex items-start gap-2">
                      <span className="text-[var(--accent-purple)] mt-0.5">&rarr;</span> {r}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* Analyze Modal */}
      <Modal open={showAnalyze} onClose={() => setShowAnalyze(false)} title="Analyze Market Signals">
        <div className="space-y-4">
          <Input
            label="Domain"
            value={analyzeDomain}
            onChange={(e) => setAnalyzeDomain(e.target.value)}
            placeholder="e.g., B2B sales automation"
          />
          <Textarea
            label="Market Data (paste news, research, competitor info)"
            value={analyzeText}
            onChange={(e) => setAnalyzeText(e.target.value)}
            rows={8}
            placeholder="Paste market research, competitor announcements, industry news, job postings, funding news..."
          />
          <Input
            label="Focus Areas (comma-separated)"
            value={analyzeFocus}
            onChange={(e) => setAnalyzeFocus(e.target.value)}
            placeholder="pricing, competitors, market size"
          />
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="ghost" onClick={() => setShowAnalyze(false)}>Cancel</Button>
            <Button onClick={handleAnalyze} disabled={loading}>
              {loading ? "Analyzing..." : "Analyze"}
            </Button>
          </div>
        </div>
      </Modal>

      {/* Score Opportunity Modal */}
      <Modal open={showScore} onClose={() => { setShowScore(false); setOppScore(null); }} title="Score Opportunity">
        <div className="space-y-4">
          <Textarea
            label="Opportunity Description"
            value={oppDescription}
            onChange={(e) => setOppDescription(e.target.value)}
            rows={3}
            placeholder="Describe the opportunity..."
          />
          <Input
            label="Domain"
            value={oppDomain}
            onChange={(e) => setOppDomain(e.target.value)}
            placeholder="e.g., AI-powered sales tools"
          />
          {oppScore && (
            <Card className="border-green-500/30">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-medium text-green-400">Overall Score</span>
                <span className="text-xl font-bold text-green-300">{(oppScore.overall_score * 100).toFixed(0)}%</span>
              </div>
              <div className="text-sm text-[var(--text-secondary)] space-y-1">
                <p>Market Size: {oppScore.market_size_signal}</p>
                <p>Competition: {oppScore.competition_level}</p>
                <p>Timing: {oppScore.timing}</p>
              </div>
            </Card>
          )}
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="ghost" onClick={() => { setShowScore(false); setOppScore(null); }}>Close</Button>
            <Button onClick={handleScoreOpportunity}>Score</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
