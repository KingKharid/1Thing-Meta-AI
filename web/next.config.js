/** @type {import('next').NextConfig} */
const nextConfig = {
  // Emit a self-contained server bundle. Both Vercel and the Modal demo
  // host can run it; without this the Modal image would need the full
  // node_modules tree at runtime.
  output: "standalone",
};

module.exports = nextConfig;
