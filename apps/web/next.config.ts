import path from "node:path";
import type { NextConfig } from "next";

const apiBaseUrl = (process.env.GRADMATCH_API_BASE_URL ?? "http://localhost:8000").replace(
  /\/$/u,
  "",
);

const nextConfig: NextConfig = {
  devIndicators: false,
  experimental: {
    extensionAlias: {
      ".js": [".ts", ".tsx", ".js"],
      ".jsx": [".tsx", ".jsx"],
    },
  },
  output: "standalone",
  outputFileTracingRoot: path.join(process.cwd(), "../.."),
  transpilePackages: ["@gradmatch/api-client", "@gradmatch/design-tokens", "@gradmatch/domain"],
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${apiBaseUrl}/api/:path*` },
      { source: "/_allauth/:path*", destination: `${apiBaseUrl}/_allauth/:path*` },
      { source: "/accounts/:path*", destination: `${apiBaseUrl}/accounts/:path*` },
    ];
  },
};

export default nextConfig;
