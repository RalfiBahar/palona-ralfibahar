import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/uploads",
        destination: "http://localhost:8000/tools/uploads",
      },
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/:path*",
      },
      {
        source: "/uploads/:path*",
        destination: "http://localhost:8000/uploads/:path*",
      },
    ];
  },
};

export default nextConfig;
