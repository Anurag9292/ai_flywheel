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
      } catch {
        // If API is not available, show zeros
      } finally {
        setLoading(false);
      }
    }
    loadStats();
  }, []);

  const cards = [
    { title: "Ventures", value: stats.ventures },
    { title: "Agents", value: stats.agents },
    { title: "Active Experiments", value: stats.experiments },
    { title: "Monthly Cost", value: stats.cost },
  ];

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Welcome to AI Flywheel</h1>

      {loading ? (
        <p className="text-gray-500">Loading dashboard...</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {cards.map((card) => (
            <div
              key={card.title}
              className="bg-white rounded-lg shadow p-6"
            >
              <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide">
                {card.title}
              </h3>
              <p className="mt-2 text-3xl font-bold text-gray-900">{card.value}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
