"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { PageHeader, Card, Button, Modal, VentureSelector, Spinner, EmptyState, Badge, Input, Textarea } from "@/components/ui";

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
      <PageHeader
        title="Offer Design Engine"
        subtitle="ICP, positioning, pricing, and conversion copy. Design offers that resonate."
        actions={
          <div className="flex gap-3 items-center">
            <VentureSelector value={selectedVenture} onChange={(id) => { setSelectedVenture(id); setSelectedOffer(null); }} />
            {selectedVenture && (
              <Button onClick={() => setShowCreate(true)}>+ New Offer</Button>
            )}
          </div>
        }
      />

      <div className="grid grid-cols-3 gap-6">
        {/* Offer list */}
        <div className="col-span-1 space-y-3">
          {loading ? (
            <Spinner text="Loading..." />
          ) : offers.length === 0 && selectedVenture ? (
            <EmptyState message="No offers yet." />
          ) : (
            offers.map((offer) => (
              <Card
                key={offer.id}
                active={selectedOffer?.id === offer.id}
                onClick={() => setSelectedOffer(offer)}
                padding="sm"
              >
                <h3 className="font-medium text-[var(--text-primary)] text-sm">{offer.name}</h3>
                <div className="mt-2 flex flex-wrap gap-2">
                  <Badge variant={offer.icp ? "green" : "purple"}>
                    ICP {offer.icp ? "+" : "-"}
                  </Badge>
                  <Badge variant={offer.positioning ? "green" : "purple"}>
                    Position {offer.positioning ? "+" : "-"}
                  </Badge>
                  <Badge variant={offer.pricing ? "green" : "purple"}>
                    Pricing {offer.pricing ? "+" : "-"}
                  </Badge>
                </div>
              </Card>
            ))
          )}
        </div>

        {/* Detail */}
        <div className="col-span-2">
          {selectedOffer ? (
            <div className="space-y-4">
              {/* Action buttons */}
              <Card>
                <h2 className="text-lg font-bold text-[var(--text-primary)] mb-3">{selectedOffer.name}</h2>
                <div className="flex flex-wrap gap-2">
                  <Button size="sm" onClick={handleGenerateICP} disabled={!!generating}>
                    {generating === "icp" ? "Generating..." : "Generate ICP"}
                  </Button>
                  <Button size="sm" onClick={handleGeneratePositioning} disabled={!!generating}>
                    {generating === "positioning" ? "Generating..." : "Generate Positioning"}
                  </Button>
                  <Button size="sm" onClick={handleGeneratePricing} disabled={!!generating}>
                    {generating === "pricing" ? "Generating..." : "Generate Pricing"}
                  </Button>
                  <Button size="sm" onClick={handleGenerateLandingCopy} disabled={!!generating} className="!from-purple-600 !to-violet-700">
                    {generating === "copy" ? "Generating..." : "Generate Landing Copy"}
                  </Button>
                </div>
              </Card>

              {/* ICP Section */}
              {selectedOffer.icp && (
                <Card>
                  <h3 className="text-sm font-semibold text-[var(--text-secondary)] mb-2">Ideal Customer Profile</h3>
                  <pre className="text-xs text-[var(--text-muted)] whitespace-pre-wrap code-block p-3 rounded">
                    {JSON.stringify(selectedOffer.icp, null, 2)}
                  </pre>
                </Card>
              )}

              {/* Positioning */}
              {selectedOffer.positioning && (
                <Card>
                  <h3 className="text-sm font-semibold text-[var(--text-secondary)] mb-2">Positioning Strategy</h3>
                  <pre className="text-xs text-[var(--text-muted)] whitespace-pre-wrap code-block p-3 rounded">
                    {JSON.stringify(selectedOffer.positioning, null, 2)}
                  </pre>
                </Card>
              )}

              {/* Pricing */}
              {selectedOffer.pricing && (
                <Card>
                  <h3 className="text-sm font-semibold text-[var(--text-secondary)] mb-2">Pricing Strategy</h3>
                  <pre className="text-xs text-[var(--text-muted)] whitespace-pre-wrap code-block p-3 rounded">
                    {JSON.stringify(selectedOffer.pricing, null, 2)}
                  </pre>
                </Card>
              )}

              {/* Landing Copy */}
              {landingCopy && (
                <Card className="border-[var(--accent-purple)]/30">
                  <h3 className="text-sm font-semibold text-[var(--accent-purple)] mb-3">Landing Page Copy</h3>
                  <div className="space-y-4">
                    <div className="text-center py-6 bg-gradient-to-b from-[var(--accent-purple)]/10 to-transparent rounded-lg">
                      <h1 className="text-2xl font-bold text-[var(--text-primary)]">{landingCopy.headline}</h1>
                      <p className="text-lg text-[var(--text-secondary)] mt-2">{landingCopy.subheadline}</p>
                      <p className="text-sm text-[var(--text-muted)] mt-3 max-w-md mx-auto">{landingCopy.hero_body}</p>
                      <div className="mt-4 flex justify-center gap-3">
                        <span className="btn-glow !text-sm">{landingCopy.cta_primary}</span>
                        <span className="btn-ghost !text-sm">{landingCopy.cta_secondary}</span>
                      </div>
                    </div>
                    {landingCopy.benefits?.length > 0 && (
                      <div>
                        <h4 className="text-xs font-medium text-[var(--text-muted)] mb-2">Benefits</h4>
                        <ul className="grid grid-cols-2 gap-2">
                          {landingCopy.benefits.map((b: string, i: number) => (
                            <li key={i} className="text-sm text-[var(--text-secondary)] flex items-start gap-2">
                              <span className="text-green-400">+</span> {b}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </Card>
              )}
            </div>
          ) : (
            <EmptyState message="Select an offer to view and generate components" />
          )}
        </div>
      </div>

      {/* Create Modal */}
      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="New Offer">
        <div className="space-y-4">
          <Input label="Name" value={formName} onChange={(e) => setFormName(e.target.value)} placeholder="e.g., AI Sales Coach Pro" />
          <Input label="Domain" value={formDomain} onChange={(e) => setFormDomain(e.target.value)} placeholder="e.g., B2B sales automation" />
          <Input label="Target Audience" value={formAudience} onChange={(e) => setFormAudience(e.target.value)} placeholder="e.g., B2B SDRs at companies with 50-500 employees" />
          <Textarea label="Problem Statement" value={formProblem} onChange={(e) => setFormProblem(e.target.value)} rows={2} placeholder="What pain are you solving?" />
          <Textarea label="Solution Description" value={formSolution} onChange={(e) => setFormSolution(e.target.value)} rows={2} placeholder="How does your product solve it?" />
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="ghost" onClick={() => setShowCreate(false)}>Cancel</Button>
            <Button onClick={handleCreate}>Create Offer</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
