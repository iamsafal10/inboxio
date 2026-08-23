import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/auth/:path*",
        destination: "http://127.0.0.1:8000/auth/:path*",
      },
      {
        source: "/api/:path*",
        destination: "http://127.0.0.1:8000/api/:path*",
      },
      {
        source: "/chat",
        destination: "http://127.0.0.1:8000/chat",
      },
      {
        source: "/cold_email/:path*",
        destination: "http://127.0.0.1:8000/cold_email/:path*",
      },
      {
        source: "/gmail/:path*",
        destination: "http://127.0.0.1:8000/gmail/:path*",
      },
      {
        source: "/baseline/:path*",
        destination: "http://127.0.0.1:8000/baseline/:path*",
      },
    ];
  },
};

export default nextConfig;
