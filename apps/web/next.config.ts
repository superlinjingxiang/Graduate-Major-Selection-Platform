import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  outputFileTracingRoot: path.join(process.cwd(), "../.."),
  transpilePackages: ["@gradmatch/api-client", "@gradmatch/design-tokens", "@gradmatch/domain"],
};

export default nextConfig;
