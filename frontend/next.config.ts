import type { NextConfig } from "next";

// The dev introspection API (FastAPI) runs as a separate process. Proxy
// /api/* to it server-side so the browser only ever talks to the frontend
// origin — this keeps the preview working regardless of the exposed hostname.
// Override with FLYWHEEL_API_ORIGIN if the backend runs elsewhere.
const API_ORIGIN = process.env.FLYWHEEL_API_ORIGIN ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  // Next 16 blocks cross-origin dev resources (HMR, chunks) by default. The
  // Cord preview serves the app from a *.preview-cord.xyz host, so allow it in
  // development or the client bundle never hydrates through the preview proxy.
  allowedDevOrigins: [
    "preview-cord.xyz",
    "p-faa36726-605a-4639-a9f8-ec68d04bd667-3000.preview-cord.xyz",
  ],
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${API_ORIGIN}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
