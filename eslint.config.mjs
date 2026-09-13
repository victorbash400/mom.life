import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";

export default defineConfig([
  ...nextVitals,
  globalIgnores([".build/**", ".next/**", ".vercel/**", "next-env.d.ts", "backend/.venv/**", "backend/.sessions/**", "backend/data/**"]),
]);
