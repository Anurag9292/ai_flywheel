"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";

interface Offer {
  id: string;
  venture_id: string;
  name: string;
  status: string;
  icp: any | null;
  positioning: any | null;
  pricing: any | null;
  messaging: any | null;
  objection_rebuttals: any[] | null;
  version: number;
  created_at: string;
}

export default function OffersPage() {
  const [ventures, setVentures] = useState<any[]>([]);
  const [selectedVenture, setSelectedVenture] = useState("");
  const [offers, setOffers] = useState<Offer[]>([]);
  const [selectedOffer, setSelectedOffer] = useState<Offer | null>(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState("");

  // Create form
  const [showCreate, setShowCreate] = useState(false);
  const [formName, setFormName] = useState("");
  const [formDomain, setFormDomain] = useState("");
  const [formAudience, setFormAudience] = useState("");
  const [formProblem, setFormProblem] = useState("");
  const [formSolution, setFormSolution] = useState("");

  // Landing copy result
  const [landingCopy, setLandingCopy] = useState<any>(null);

  useEffect(() => {
    api.ventures.list().then(setVentures).catch(() => {});
  }, []);

  useEffect(() => {
    if (selectedVenture) {
      setLoading(true);
      api.offers
        .list(selectedVenture)
        .then(setOffers)
        .catch(() => setOffers([]))
        .finally(() => setLoading(false));
    }
  }, [selectedVenture]);

  async function handleCreate() {
    if (!selectedVenture) return;
    const offer = await api.offers.create(selectedVenture, {
      name: formName,
      domain: formDomain,
      target_audience: formAudience,
      problem_statement: formProblem,
      solution_description: formSolution,
    });
    setOffers([...offers, offer]);
    setSelectedOffer(offer);
    setShowCreate(false);
    setFormName("");
    setFormDomain("");
    setFormAudience("");
    setFormProblem("");
    setFormSolution("");
  }

  async function handleGenerateICP() {
    if (!selectedOffer) return;
    setGenerating("icp");
    try {
      await api.offers.generateICP(selectedVenture, {
        offer_id: selectedOffer.id,
        domain: formDomain || selectedOffer.name,
        initial_description: formAudience || "Target customers",
      });
      await refreshOffer();
    } finally {
      setGenerating("");
    }
  }

  async function handleGeneratePositioning() {
    if (!selectedOffer) return;
    setGenerating("positioning");
    try {
      await api.offers.generatePositioning(selectedVenture, {
        offer_id: selectedOffer.id,
        domain: formDomain || selectedOffer.name,
      });
      await refreshOffer();
    } finally {
      setGenerating("");
    }
  }

  async function handleGeneratePricing() {
    if (!selectedOffer) return;
    setGenerating("pricing");
    try {
      await api.offers.generatePricing(selectedVenture, {
        offer_id: selectedOffer.id,
        value_delivered: "AI-powered productivity enhancement",
        target_segment: "SMB",
      });
      await refreshOffer();
    } finally {
      setGenerating("");
    }
  }

  async function handleGenerateLandingCopy() {
    if (!selectedOffer) return;
    setGenerating("copy");
    try {
      const result = await api.offers.generateLandingCopy(selectedVenture, {
        offer_id: selectedOffer.id,
        tone: "professional",
      });
      setLandingCopy(result);
    } finally {
      setGenerating("");
    }
  }

  async function refreshOffer() {
    const updated = await api.offers.list(selectedVenture);
    setOffers(updated);
    const refreshed = updated.find((o: Offer) => o.id === selectedOffer?.id);
    if (refreshed) setSelectedOffer(refreshed);
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Offer Design Engine</h1>
          <p className="text-sm text-gray-500 mt-1">
            ICP, positioning, pricing, and conversion copy. Design offers that resonate.
          </p>
        </div>
        <div className="flex gap-3">
          <select
            value={selectedVenture}
            onChange={(e) => { setSelectedVenture(e.target.value); setSelectedOffer(null); }}
            className="rounded-md border border-gray-300 px-3 py-2 text-sm"
          >
            <option value="">Select venture...</option>
            {ventures.map((v) => (
              <option key={v.id} value={v.id}>{v.name}</option>
            ))}
          </select>
          {selectedVenture && (
            <button
              onClick={() => setShowCreate(true)}
              className="bg-indigo-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-indigo-700"
            >
              + New Offer
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Offer list */}
        <div className="col-span-1 space-y-3">
          {loading ? (
            <p className="text-sm text-gray-500">Loading...</p>
          ) : offers.length === 0 && selectedVenture ? (
            <div className="bg-white rounded-lg border border-dashed border-gray-300 p-6 text-center">
              <p className="text-gray-500 text-sm">No offers yet.</p>
            </div>
          ) : (
            offers.map((offer) => (
              <div
                key={offer.id}
                onClick={() => setSelectedOffer(offer)}
                className={`bg-white rounded-lg border p-4 cursor-pointer transition-all ${
                  selectedOffer?.id === offer.id ? "border-indigo-500 ring-2 ring-indigo-200" : "border-gray-200 hover:border-gray-300"
                }`}
              >
                <h3 className="font-medium text-gray-900 text-sm">{offer.name}</h3>
                <div className="mt-2 flex flex-wrap gap-2">
                  <span className={`text-xs px-2 py-0.5 rounded ${offer.icp ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                    ICP {offer.icp ? "+" : "-"}
                  </span>
                  <span className={`text-xs px-2 py-0.5 rounded ${offer.positioning ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                    Position {offer.positioning ? "+" : "-"}
                  </span>
                  <span className={`text-xs px-2 py-0.5 rounded ${offer.pricing ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                    Pricing {offer.pricing ? "+" : "-"}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Detail */}
        <div className="col-span-2">
          {selectedOffer ? (
            <div className="space-y-4">
              {/* Action buttons */}
              <div className="bg-white rounded-lg border border-gray-200 p-4">
                <h2 className="text-lg font-bold text-gray-900 mb-3">{selectedOffer.name}</h2>
                <div className="flex flex-wrap gap-2">
                  <button onClick={handleGenerateICP} disabled={!!generating} className="bg-indigo-600 text-white px-3 py-1.5 rounded text-sm hover:bg-indigo-700 disabled:opacity-50">
                    {generating === "icp" ? "Generating..." : "Generate ICP"}
                  </button>
                  <button onClick={handleGeneratePositioning} disabled={!!generating} className="bg-indigo-600 text-white px-3 py-1.5 rounded text-sm hover:bg-indigo-700 disabled:opacity-50">
                    {generating === "positioning" ? "Generating..." : "Generate Positioning"}
                  </button>
                  <button onClick={handleGeneratePricing} disabled={!!generating} className="bg-indigo-600 text-white px-3 py-1.5 rounded text-sm hover:bg-indigo-700 disabled:opacity-50">
                    {generating === "pricing" ? "Generating..." : "Generate Pricing"}
                  </button>
                  <button onClick={handleGenerateLandingCopy} disabled={!!generating} className="bg-purple-600 text-white px-3 py-1.5 rounded text-sm hover:bg-purple-700 disabled:opacity-50">
                    {generating === "copy" ? "Generating..." : "Generate Landing Copy"}
                  </button>
                </div>
              </div>

              {/* ICP Section */}
              {selectedOffer.icp && (
                <div className="bg-white rounded-lg border border-gray-200 p-4">
                  <h3 className="text-sm font-semibold text-gray-700 mb-2">Ideal Customer Profile</h3>
                  <pre className="text-xs text-gray-600 whitespace-pre-wrap bg-gray-50 p-3 rounded">
                    {JSON.stringify(selectedOffer.icp, null, 2)}
                  </pre>
                </div>
              )}

              {/* Positioning */}
              {selectedOffer.positioning && (
                <div className="bg-white rounded-lg border border-gray-200 p-4">
                  <h3 className="text-sm font-semibold text-gray-700 mb-2">Positioning Strategy</h3>
                  <pre className="text-xs text-gray-600 whitespace-pre-wrap bg-gray-50 p-3 rounded">
                    {JSON.stringify(selectedOffer.positioning, null, 2)}
                  </pre>
                </div>
              )}

              {/* Pricing */}
              {selectedOffer.pricing && (
                <div className="bg-white rounded-lg border border-gray-200 p-4">
                  <h3 className="text-sm font-semibold text-gray-700 mb-2">Pricing Strategy</h3>
                  <pre className="text-xs text-gray-600 whitespace-pre-wrap bg-gray-50 p-3 rounded">
                    {JSON.stringify(selectedOffer.pricing, null, 2)}
                  </pre>
                </div>
              )}

              {/* Landing Copy */}
              {landingCopy && (
                <div className="bg-white rounded-lg border border-purple-200 p-4">
                  <h3 className="text-sm font-semibold text-purple-700 mb-3">Landing Page Copy</h3>
                  <div className="space-y-4">
                    <div className="text-center py-6 bg-gradient-to-b from-purple-50 to-white rounded-lg">
                      <h1 className="text-2xl font-bold text-gray-900">{landingCopy.headline}</h1>
                      <p className="text-lg text-gray-600 mt-2">{landingCopy.subheadline}</p>
                      <p className="text-sm text-gray-500 mt-3 max-w-md mx-auto">{landingCopy.hero_body}</p>
                      <div className="mt-4 flex justify-center gap-3">
                        <span className="bg-indigo-600 text-white px-4 py-2 rounded-md text-sm">{landingCopy.cta_primary}</span>
                        <span className="border border-gray-300 text-gray-700 px-4 py-2 rounded-md text-sm">{landingCopy.cta_secondary}</span>
                      </div>
                    </div>
                    {landingCopy.benefits?.length > 0 && (
                      <div>
                        <h4 className="text-xs font-medium text-gray-500 mb-2">Benefits</h4>
                        <ul className="grid grid-cols-2 gap-2">
                          {landingCopy.benefits.map((b: string, i: number) => (
                            <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                              <span className="text-green-500">+</span> {b}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="bg-white rounded-lg border border-dashed border-gray-300 p-12 text-center">
              <p className="text-gray-500">Select an offer to view and generate components</p>
            </div>
          )}
        </div>
      </div>

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-lg shadow-xl space-y-4">
            <h2 className="text-lg font-bold text-gray-900">New Offer</h2>
            <div>
              <label className="text-sm font-medium text-gray-700">Name</label>
              <input value={formName} onChange={(e) => setFormName(e.target.value)} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm" placeholder="e.g., AI Sales Coach Pro" />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700">Domain</label>
              <input value={formDomain} onChange={(e) => setFormDomain(e.target.value)} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm" placeholder="e.g., B2B sales automation" />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700">Target Audience</label>
              <input value={formAudience} onChange={(e) => setFormAudience(e.target.value)} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm" placeholder="e.g., B2B SDRs at companies with 50-500 employees" />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700">Problem Statement</label>
              <textarea value={formProblem} onChange={(e) => setFormProblem(e.target.value)} rows={2} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm" placeholder="What pain are you solving?" />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700">Solution Description</label>
              <textarea value={formSolution} onChange={(e) => setFormSolution(e.target.value)} rows={2} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm" placeholder="How does your product solve it?" />
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-sm text-gray-700">Cancel</button>
              <button onClick={handleCreate} className="bg-indigo-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-indigo-700">Create Offer</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
