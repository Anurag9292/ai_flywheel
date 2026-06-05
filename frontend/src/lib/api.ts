const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

// Simple token storage (in-memory for now)
let authToken: string | null = null;

export function setAuthToken(token: string | null) {
  authToken = token;
  if (token) {
    if (typeof window !== "undefined") {
      localStorage.setItem("flywheel_token", token);
    }
  } else {
    if (typeof window !== "undefined") {
      localStorage.removeItem("flywheel_token");
    }
  }
}

export function getAuthToken(): string | null {
  if (authToken) return authToken;
  if (typeof window !== "undefined") {
    return localStorage.getItem("flywheel_token");
  }
  return null;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public body?: any
  ) {
    super(`API error: ${status} ${statusText}`);
  }
}

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getAuthToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options?.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    let body;
    try {
      body = await res.json();
    } catch {
      body = null;
    }
    throw new ApiError(res.status, res.statusText, body);
  }

  return res.json();
}

// Auth API
export const authApi = {
  login: (email: string, password: string = "") =>
    apiFetch<{ access_token: string; user: any }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: () => apiFetch<{ id: string; email: string; ventures: string[] }>("/api/auth/me"),
};

// Typed API functions
export const api = {
  health: () => apiFetch<any>("/health"),
  ventures: {
    list: () => apiFetch<any[]>("/api/ventures/"),
    create: (data: { name: string; domain: string }) =>
      apiFetch<any>("/api/ventures/", { method: "POST", body: JSON.stringify(data) }),
    get: (id: string) => apiFetch<any>(`/api/ventures/${id}`),
  },
  agents: {
    list: (ventureId: string) =>
      apiFetch<any[]>(`/api/agents/?venture_id=${ventureId}`),
    create: (ventureId: string, data: any) =>
      apiFetch<any>(`/api/agents/?venture_id=${ventureId}`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    execute: (ventureId: string, data: any) =>
      apiFetch<any>(`/api/agents/execute?venture_id=${ventureId}`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },
  discovery: {
    listProjects: (ventureId: string) =>
      apiFetch<any[]>(`/api/discovery/projects?venture_id=${ventureId}`),
    createProject: (ventureId: string, data: any) =>
      apiFetch<any>(`/api/discovery/projects?venture_id=${ventureId}`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    generateGuide: (ventureId: string, data: any) =>
      apiFetch<any>(`/api/discovery/interview-guide?venture_id=${ventureId}`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    analyzeTranscript: (ventureId: string, data: any) =>
      apiFetch<any>(`/api/discovery/analyze-transcript?venture_id=${ventureId}`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    synthesize: (ventureId: string, data: any) =>
      apiFetch<any>(`/api/discovery/synthesize?venture_id=${ventureId}`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },
  experiments: {
    list: (ventureId: string) =>
      apiFetch<any[]>(`/api/experiments/?venture_id=${ventureId}`),
    getResults: (ventureId: string, id: string) =>
      apiFetch<any>(`/api/experiments/${id}/results?venture_id=${ventureId}`),
  },
  costs: {
    report: (ventureId: string) =>
      apiFetch<any>(`/api/costs/report?venture_id=${ventureId}`),
    alerts: (ventureId: string) =>
      apiFetch<any[]>(`/api/costs/alerts?venture_id=${ventureId}`),
  },
  reviews: {
    queue: (ventureId: string) =>
      apiFetch<any>(`/api/reviews/queue?venture_id=${ventureId}`),
    decide: (ventureId: string, data: { review_id: string; decision: string; notes?: string }) =>
      apiFetch<any>(`/api/reviews/decide?venture_id=${ventureId}`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },
  thesis: {
    list: (ventureId: string) =>
      apiFetch<any[]>(`/api/thesis/?venture_id=${ventureId}`),
    create: (ventureId: string, data: any) =>
      apiFetch<any>(`/api/thesis/?venture_id=${ventureId}`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    get: (ventureId: string, id: string) =>
      apiFetch<any>(`/api/thesis/${id}?venture_id=${ventureId}`),
    addEvidence: (ventureId: string, data: any) =>
      apiFetch<any>(`/api/thesis/evidence?venture_id=${ventureId}`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    generateValidationPlan: (ventureId: string, data: any) =>
      apiFetch<any>(`/api/thesis/validation-plan?venture_id=${ventureId}`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    generateMemo: (ventureId: string, data: any) =>
      apiFetch<any>(`/api/thesis/memo?venture_id=${ventureId}`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },
  market: {
    analyzeSignals: (ventureId: string, data: any) =>
      apiFetch<any>(`/api/market/analyze?venture_id=${ventureId}`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    getSignals: (ventureId: string) =>
      apiFetch<any[]>(`/api/market/signals?venture_id=${ventureId}`),
    generateReport: (ventureId: string, data: any) =>
      apiFetch<any>(`/api/market/report?venture_id=${ventureId}`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    scoreOpportunity: (ventureId: string, description: string, domain: string) =>
      apiFetch<any>(`/api/market/score-opportunity?venture_id=${ventureId}&opportunity_description=${encodeURIComponent(description)}&domain=${encodeURIComponent(domain)}`, {
        method: "POST",
      }),
  },
  offers: {
    list: (ventureId: string) =>
      apiFetch<any[]>(`/api/offers/?venture_id=${ventureId}`),
    create: (ventureId: string, data: any) =>
      apiFetch<any>(`/api/offers/?venture_id=${ventureId}`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    generateICP: (ventureId: string, data: any) =>
      apiFetch<any>(`/api/offers/icp?venture_id=${ventureId}`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    generatePositioning: (ventureId: string, data: any) =>
      apiFetch<any>(`/api/offers/positioning?venture_id=${ventureId}`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    generatePricing: (ventureId: string, data: any) =>
      apiFetch<any>(`/api/offers/pricing?venture_id=${ventureId}`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    generateLandingCopy: (ventureId: string, data: any) =>
      apiFetch<any>(`/api/offers/landing-copy?venture_id=${ventureId}`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },
};
