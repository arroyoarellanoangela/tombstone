import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// GitHub Pages serves a project site from /<repo>/, not from the domain root,
// so every asset URL needs that prefix baked in at build time. Local dev and
// any root-domain host (Vercel, Netlify) still want "/", which is why this is
// an env var set only by the Pages workflow rather than a hardcoded default.
const base = process.env.VITE_BASE ?? "/";

export default defineConfig({
  base,
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    host: true,
  },
});
