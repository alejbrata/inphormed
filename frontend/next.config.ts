import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'}/api/:path*`,
      },
    ];
  },
  experimental: {
    serverActions: {
      allowedOrigins: ['*'],
    },
  },
};

export default nextConfig;
