"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { PageHeader, Card, Button, Modal, Spinner, EmptyState, Badge, Input } from "@/components/ui";
import { statusVariant } from "@/components/ui/badge";

export default function VenturesPage() {
  const [ventures, setVentures] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({ name: "", domain: "" });
  const [submitting, setSubmitting] = useState(false);

  async function loadVentures() {
    try {
      setLoading(true);
      const data = await api.ventures.list();
      setVentures(data);
      setError("");
    } catch (e: any) {
      setError(e.message || "Failed to load ventures");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadVentures();
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api.ventures.create(formData);
      setFormData({ name: "", domain: "" });
      setShowForm(false);
      await loadVentures();
    } catch (e: any) {
      setError(e.message || "Failed to create venture");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Ventures"
        actions={
          <Button onClick={() => setShowForm(!showForm)}>
            {showForm ? "Cancel" : "Create Venture"}
          </Button>
        }
      />

      {error && (
        <div className="glass-card border-red-500/30 p-4 text-sm text-red-400">
          {error}
        </div>
      )}

      {loading ? (
        <Spinner text="Loading ventures..." />
      ) : ventures.length === 0 ? (
        <EmptyState message="No ventures found." hint="Create one to get started." />
      ) : (
        <Card padding="sm" className="overflow-hidden">
          <table className="min-w-full">
            <thead>
              <tr className="border-b border-[var(--border-subtle)]">
                <th className="px-6 py-3 text-left text-xs font-medium text-[var(--text-muted)] uppercase tracking-wider">Name</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-[var(--text-muted)] uppercase tracking-wider">Domain</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-[var(--text-muted)] uppercase tracking-wider">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-[var(--text-muted)] uppercase tracking-wider">Created</th>
              </tr>
            </thead>
            <tbody>
              {ventures.map((venture) => (
                <tr key={venture.id} className="border-b border-[var(--border-subtle)] last:border-0">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-[var(--text-primary)]">{venture.name}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-[var(--text-secondary)]">{venture.domain}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <Badge variant={statusVariant(venture.status || "active")}>
                      {venture.status || "active"}
                    </Badge>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-[var(--text-muted)]">
                    {venture.created_at ? new Date(venture.created_at).toLocaleDateString() : "\u2014"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      {/* Create Venture Modal */}
      <Modal open={showForm} onClose={() => setShowForm(false)} title="Create Venture">
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="Name"
            type="text"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            required
          />
          <Input
            label="Domain"
            type="text"
            value={formData.domain}
            onChange={(e) => setFormData({ ...formData, domain: e.target.value })}
            required
          />
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="ghost" type="button" onClick={() => setShowForm(false)}>Cancel</Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? "Creating..." : "Create"}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
