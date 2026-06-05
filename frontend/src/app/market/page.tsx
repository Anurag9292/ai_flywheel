"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";

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
  const [ventures, setVentures] = useState<any[]>([]);
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
    api.ventures.list().then(setVentures).catch(() => {});
  }, []);

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

  function getSignalTypeColor(type: string) {
    const colors: Record<string, string> = {
      competitor: "bg-purple-100 text-purple-700",
      trend: "bg-blue-100 text-blue-700",
      opportunity: "bg-green-100 text-green-700",
      threat: "bg-red-100 text-red-700",
      regulatory: "bg-orange-100 text-orange-700",
      funding: "bg-indigo-100 text-indigo-700",
    };
    return colors[type] || "bg-gray-100 text-gray-700";
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Market & Signal Intelligence</h1>
          <p className="text-sm text-gray-500 mt-1">
            Monitor competitors, detect trends, score opportunities. Evidence over gut feel.
          </p>
        </div>
        <div className="flex gap-3">
          <select
            value={selectedVenture}
            onChange={(e) => setSelectedVenture(e.target.value)}
            className="rounded-md border border-gray-300 px-3 py-2 text-sm"
          >
            <option value="">Select venture...</option>
            {ventures.map((v) => (
              <option key={v.id} value={v.id}>{v.name}</option>
            ))}
          </select>
          {selectedVenture && (
            <>
              <button
                onClick={() => setShowAnalyze(true)}
                className="bg-indigo-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-indigo-700"
              >
                Analyze Signals
              </button>
              <button
                onClick={handleGenerateReport}
                disabled={reportLoading}
                className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-md text-sm font-medium hover:bg-gray-50"
              >
                {reportLoading ? "Generating..." : "Generate Report"}
              </button>
              <button
                onClick={() => setShowScore(true)}
                className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-md text-sm font-medium hover:bg-gray-50"
              >
                Score Opportunity
              </button>
            </>
          )}
        </div>
      </div>

      {/* Signals Grid */}
      {selectedVenture && (
        <div className="space-y-4">
          {loading ? (
            <p className="text-gray-500 text-sm">Loading signals...</p>
          ) : signals.length === 0 ? (
            <div className="bg-white rounded-lg border border-dashed border-gray-300 p-8 text-center">
              <p className="text-gray-500">No market signals detected yet.</p>
              <p className="text-gray-400 text-sm mt-1">Paste market research, news articles, or competitor data to analyze.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {signals.map((signal) => (
                <div key={signal.id} className="bg-white rounded-lg border border-gray-200 p-4">
                  <div className="flex items-start justify-between">
                    <h3 className="font-medium text-gray-900 text-sm">{signal.title}</h3>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${getSignalTypeColor(signal.signal_type)}`}>
                      {signal.signal_type}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 mt-2">{signal.summary}</p>
                  <div className="flex items-center gap-4 mt-3">
                    <div className="flex items-center gap-1">
                      <span className="text-xs text-gray-500">Relevance:</span>
                      <div className="w-16 bg-gray-200 rounded-full h-1.5">
                        <div
                          className="h-1.5 rounded-full bg-blue-500"
                          style={{ width: `${signal.relevance_score * 100}%` }}
                        />
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      <span className="text-xs text-gray-500">Impact:</span>
                      <div className="w-16 bg-gray-200 rounded-full h-1.5">
                        <div
                          className="h-1.5 rounded-full bg-orange-500"
                          style={{ width: `${signal.impact_score * 100}%` }}
                        />
                      </div>
                    </div>
                  </div>
                  {signal.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {signal.tags.map((tag, i) => (
                        <span key={i} className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Analysis Result */}
      {analysisResult && (
        <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-6 space-y-4">
          <h3 className="text-sm font-semibold text-indigo-800">Analysis Result</h3>
          <p className="text-sm text-indigo-700">{analysisResult.summary}</p>
          {analysisResult.patterns?.length > 0 && (
            <div>
              <h4 className="text-xs font-medium text-indigo-600 mb-1">Patterns Detected:</h4>
              <ul className="list-disc list-inside text-sm text-indigo-700">
                {analysisResult.patterns.map((p: string, i: number) => (
                  <li key={i}>{p}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Report Modal */}
      {showReport && report && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-2xl shadow-xl space-y-4 max-h-[80vh] overflow-y-auto">
            <div className="flex justify-between items-start">
              <h2 className="text-lg font-bold text-gray-900">Market Intelligence Report</h2>
              <button onClick={() => setShowReport(false)} className="text-gray-400 hover:text-gray-600">&times;</button>
            </div>
            <div className="prose prose-sm max-w-none">
              <p className="whitespace-pre-wrap">{report.content}</p>
            </div>
            {report.key_findings?.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-2">Key Findings</h3>
                <ul className="space-y-1">
                  {report.key_findings.map((f: string, i: number) => (
                    <li key={i} className="text-sm text-gray-600 flex items-start gap-2">
                      <span className="text-green-500 mt-0.5">+</span> {f}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {report.recommendations?.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-2">Recommendations</h3>
                <ul className="space-y-1">
                  {report.recommendations.map((r: string, i: number) => (
                    <li key={i} className="text-sm text-gray-600 flex items-start gap-2">
                      <span className="text-blue-500 mt-0.5">→</span> {r}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Analyze Modal */}
      {showAnalyze && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-lg shadow-xl space-y-4">
            <h2 className="text-lg font-bold text-gray-900">Analyze Market Signals</h2>
            <div>
              <label className="text-sm font-medium text-gray-700">Domain</label>
              <input
                value={analyzeDomain}
                onChange={(e) => setAnalyzeDomain(e.target.value)}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                placeholder="e.g., B2B sales automation"
              />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700">Market Data (paste news, research, competitor info)</label>
              <textarea
                value={analyzeText}
                onChange={(e) => setAnalyzeText(e.target.value)}
                rows={8}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono"
                placeholder="Paste market research, competitor announcements, industry news, job postings, funding news..."
              />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700">Focus Areas (comma-separated)</label>
              <input
                value={analyzeFocus}
                onChange={(e) => setAnalyzeFocus(e.target.value)}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                placeholder="pricing, competitors, market size"
              />
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button onClick={() => setShowAnalyze(false)} className="px-4 py-2 text-sm text-gray-700">Cancel</button>
              <button onClick={handleAnalyze} disabled={loading} className="bg-indigo-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-indigo-700">
                {loading ? "Analyzing..." : "Analyze"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Score Opportunity Modal */}
      {showScore && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-lg shadow-xl space-y-4">
            <h2 className="text-lg font-bold text-gray-900">Score Opportunity</h2>
            <div>
              <label className="text-sm font-medium text-gray-700">Opportunity Description</label>
              <textarea
                value={oppDescription}
                onChange={(e) => setOppDescription(e.target.value)}
                rows={3}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                placeholder="Describe the opportunity..."
              />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700">Domain</label>
              <input
                value={oppDomain}
                onChange={(e) => setOppDomain(e.target.value)}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                placeholder="e.g., AI-powered sales tools"
              />
            </div>
            {oppScore && (
              <div className="bg-green-50 border border-green-200 rounded-lg p-4 space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm font-medium text-green-800">Overall Score</span>
                  <span className="text-xl font-bold text-green-900">{(oppScore.overall_score * 100).toFixed(0)}%</span>
                </div>
                <div className="text-sm text-green-700 space-y-1">
                  <p>Market Size: {oppScore.market_size_signal}</p>
                  <p>Competition: {oppScore.competition_level}</p>
                  <p>Timing: {oppScore.timing}</p>
                </div>
              </div>
            )}
            <div className="flex justify-end gap-3 pt-2">
              <button onClick={() => { setShowScore(false); setOppScore(null); }} className="px-4 py-2 text-sm text-gray-700">Close</button>
              <button onClick={handleScoreOpportunity} className="bg-indigo-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-indigo-700">
                Score
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
