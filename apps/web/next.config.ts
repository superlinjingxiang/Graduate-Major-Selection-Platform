import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["@gradmatch/api-client", "@gradmatch/design-tokens", "@gradmatch/domain"],
};

export default nextConfig;
