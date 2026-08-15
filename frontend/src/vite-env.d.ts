/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Set by docker-compose in local dev; absent in the static build. */
  readonly VITE_API_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
