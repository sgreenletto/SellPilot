/// <reference types="vite/client" />

import "vue-router";

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_PROXY_TARGET?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

declare module "vue-router" {
  interface RouteMeta {
    title: string;
    module: string;
    description: string;
    requiresAuth?: boolean;
  }
}

export {};
