import type { NextConfig } from "next";

const backendUrl = (() => {
  // Render-style split host/port (works with Blueprint fromService)
  const host = process.env.BACKEND_HOST;
  if (host) {
    const port = process.env.BACKEND_PORT || "10000";
    const clean = host.replace(/^https?:\/\//, "").replace(/:\d+$/, "");
    return `http://${clean}:${port}`;
  }
  const raw = process.env.BACKEND_URL || "http://localhost:8000";
  return raw.startsWith("http") ? raw : `http://${raw}`;
})();

const nextConfig: NextConfig = {
  reactStrictMode: true,
  turbopack: {},
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${backendUrl}/api/v1/:path*`,
      },
      {
        source: "/health",
        destination: `${backendUrl}/health`,
      },
    ];
  },
};

export default nextConfig;
