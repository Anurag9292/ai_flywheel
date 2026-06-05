const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

// Typed API functions
export const api = {
  ventures: {
    list: () => apiFetch<any[]>("/api/ventures/"),
    create: (data: { name: string; domain: string }) =>
      apiFetch<any>("/api/ventures/", { method: "POST", body: JSON.stringify(data) }),
    get: (id: string) => apiFetch<any>(`/api/ventures/${id}`),
  },
  agents: {
    list: (ventureId: string) => apiFetch<any[]>(`/api/agents/?venture_id=${ventureId}`),
    create: (ventureId: string, data: any) =>
      apiFetch<any>(`/api/agents/?venture_id=${ventureId}`, { method: "POST", body: JSON.stringify(data) }),
    execute: (ventureId: string, data: any) =>
      apiFetch<any>(`/api/agents/execute?venture_id=${ventureId}`, { method: "POST", body: JSON.stringify(data) }),
  },
  discovery: {
    listProjects: (ventureId: string) => apiFetch<any[]>(`/api/discovery/projects?venture_id=${ventureId}`),
    createProject: (ventureId: string, data: any) =>
      apiFetch<any>(`/api/discovery/projects?venture_id=${ventureId}`, { method: "POST", body: JSON.stringify(data) }),
    generateGuide: (ventureId: string, data: any) =>
      apiFetch<any>(`/api/discovery/interview-guide?venture_id=${ventureId}`, { method: "POST", body: JSON.stringify(data) }),
  },
  experiments: {
    list: (ventureId: string) => apiFetch<any[]>(`/api/experiments/?venture_id=${ventureId}`),
    getResults: (ventureId: string, id: string) =>
      apiFetch<any>(`/api/experiments/${id}/results?venture_id=${ventureId}`),
  },
  costs: {
    report: (ventureId: string) => apiFetch<any>(`/api/costs/report?venture_id=${ventureId}`),
    alerts: (ventureId: string) => apiFetch<any[]>(`/api/costs/alerts?venture_id=${ventureId}`),
  },
};
