"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function DashboardHome() {
  const [stats, setStats] = useState({
    ventures: 0,
    agents: 0,
    experiments: 0,
    cost: "$0.00",
  });
  const [loading, setLoading] = useState(true);
  const [health, setHealth] = useState<any>(null);

  useEffect(() => {
    async function loadStats() {
      try {
        const ventures = await api.ventures.list();
        let agentCount = 0;
        let experimentCount = 0;

        for (const v of ventures) {
          try {
            const agents = await api.agents.list(v.id);
            agentCount += agents.length;
          } catch {}
          try {
            const experiments = await api.experiments.list(v.id);
            experimentCount += experiments.length;
          } catch {}
        }

        setStats({
          ventures: ventures.length,
          agents: agentCount,
          experiments: experimentCount,
          cost: "$--",
        });
      } catch {}
      try {
        const h = await api.health();
        setHealth(h);
      } catch {}
      setLoading(false);
    }
    loadStats();
  }, []);

  const cards = [
    { title: "Ventures", value: stats.ventures, icon: "M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10", color: "from-violet-500 to-purple-600" },
    { title: "Agents", value: stats.agents, icon: "M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z", color: "from-indigo-500 to-blue-600" },
    { title: "Experiments", value: stats.experiments, icon: "M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z", color: "from-cyan-500 to-teal-600" },
    { title: "Monthly Cost", value: stats.cost, icon: "M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z", color: "from-amber-500 to-orange-600" },
  ];

  return (
    <div className="space-y-8">
      {/* Hero header */}
      <div>
        <h1 className="text-4xl font-bold gradient-text">AI Flywheel</h1>
        <p className="text-[var(--text-secondary)] mt-2 text-lg">
          Personal Venture Operating System
        </p>
      </div>

      {/* Stats grid */}
      {loading ? (
        <div className="flex items-center gap-3 text-[var(--text-muted)]">
          <div className="w-4 h-4 border-2 border-violet-500/30 border-t-violet-500 rounded-full animate-spin" />
          Initializing systems...
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
          {cards.map((card) => (
            <div key={card.title} className="glass-card p-5">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-medium text-[var(--text-muted)] uppercase tracking-wider">
                    {card.title}
                  </p>
                  <p className="mt-2 text-3xl font-bold text-[var(--text-primary)]">
                    {card.value}
                  </p>
                </div>
                <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${card.color} flex items-center justify-center shadow-lg`}>
                  <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d={card.icon} />
                  </svg>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* System status */}
      {health && (
        <div className="glass-card p-6">
          <h2 className="text-sm font-semibold text-[var(--text-primary)] mb-4">System Status</h2>
          <div className="grid grid-cols-3 gap-4">
            {["database", "redis", "temporal"].map((service) => {
              const status = health[service] || "unknown";
              const isOk = status === "connected";
              return (
                <div key={service} className="flex items-center gap-3">
                  <div className={`w-2.5 h-2.5 rounded-full ${isOk ? "bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)]" : "bg-red-400 shadow-[0_0_8px_rgba(248,113,113,0.5)]"}`} />
                  <div>
                    <p className="text-sm font-medium text-[var(--text-primary)] capitalize">{service}</p>
                    <p className="text-xs text-[var(--text-muted)]">{isOk ? "Connected" : "Unavailable"}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Quick actions */}
      <div className="glass-card p-6">
        <h2 className="text-sm font-semibold text-[var(--text-primary)] mb-4">Quick Actions</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: "New Venture", href: "/ventures", icon: "M12 4v16m8-8H4" },
            { label: "Create Thesis", href: "/thesis", icon: "M9 12l2 2 4-4" },
            { label: "Run Discovery", href: "/discovery", icon: "M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" },
            { label: "Design Offer", href: "/offers", icon: "M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7" },
          ].map((action) => (
            <a
              key={action.label}
              href={action.href}
              className="flex flex-col items-center gap-2 p-4 rounded-lg border border-[var(--border-subtle)] hover:border-[var(--border-glow)] hover:bg-[rgba(139,92,246,0.05)] transition-all group"
            >
              <svg className="w-5 h-5 text-[var(--text-muted)] group-hover:text-violet-400 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d={action.icon} />
              </svg>
              <span className="text-xs font-medium text-[var(--text-secondary)] group-hover:text-[var(--text-primary)] transition-colors">{action.label}</span>
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}
