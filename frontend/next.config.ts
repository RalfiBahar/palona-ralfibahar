import type { NextConfig } from "next";

const API_BASE_URL = process.env.API_BASE_URL || "http://localhost:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/uploads",
        destination: `${API_BASE_URL}/tools/uploads`,
      },
      {
        source: "/api/:path*",
        destination: `${API_BASE_URL}/:path*`,
      },
      {
        source: "/uploads/:path*",
        destination: `${API_BASE_URL}/uploads/:path*`,
      },
    ];
  },
};

export default nextConfig;
