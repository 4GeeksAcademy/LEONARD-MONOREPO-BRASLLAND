import type { NextConfig } from "next";
import path from "node:path";

const nextConfig: NextConfig = {
  turbopack: { root: path.resolve(__dirname, "../..") },
  skipTrailingSlashRedirect: true,
  async rewrites() {
    const backend = process.env.AUTH_API_URL ?? "http://127.0.0.1:8012";
    return [
      { source: "/api/backend/:path*", destination: `${backend}/:path*` },
      { source: "/api/incidents/:path*", destination: `${backend}/api/incidents/:path*` },
      { source: "/suppliers/:path*", destination: `${backend}/suppliers/:path*` },
      { source: "/backoffice/", destination: `${backend}/backoffice/index.html` },
      { source: "/backoffice/suppliers/", destination: `${backend}/backoffice/suppliers/index.html` },
      { source: "/backoffice/:path*", destination: `${backend}/backoffice/:path*` },
    ];
  },
};

export default nextConfig;
