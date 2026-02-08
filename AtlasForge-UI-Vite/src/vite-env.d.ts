/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  readonly VITE_MONGODB_URI: string
  readonly VITE_DB_NAME: string
  readonly VITE_ENVIRONMENT: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
