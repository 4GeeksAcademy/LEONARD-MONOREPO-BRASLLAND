import type { NextConfig } from "next";
import path from "node:path";

const nextConfig: NextConfig = {
  turbopack: { root: path.resolve(__dirname, "../..") },
  skipTrailingSlashRedirect: true,
  async rewrites() {
    const backend = process.env.AUTH_API_URL ?? "http://127.0.0.1:8012";
    const inventoryBackend = (process.env.NEXT_PUBLIC_INVENTORY_API_URL ?? backend).replace(/\/$/, "");
    return [
      { source: "/api/backend/inventory/:path*", destination: `${inventoryBackend}/inventory/:path*` },
      { source: "/api/backend/:path*", destination: `${backend}/:path*` },
      { source: "/api/incidents/:path*", destination: `${backend}/api/incidents/:path*` },
      { source: "/suppliers/:path*", destination: `${backend}/suppliers/:path*` },
      { source: "/backoffice/", destination: `${backend}/backoffice/index.html` },
      { source: "/backoffice/incidents/", destination: `${backend}/backoffice/incidents/index.html` },
      { source: "/backoffice/suppliers/", destination: `${backend}/backoffice/suppliers/index.html` },
      ...["products", "orders", "orders/inbound", "orders/outbound"].flatMap((route) =>
        ["", "/"].map((suffix) => ({
          source: `/backoffice/inventory/${route}${suffix}`,
          destination: `${backend}/backoffice/inventory/index.html`,
        })),
      ),
      { source: "/backoffice/:path*", destination: `${backend}/backoffice/:path*` },
    ];
  },
};

export default nextConfig;
