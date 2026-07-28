import { fileURLToPath, URL } from "node:url";

import vue from "@vitejs/plugin-vue";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        "@": fileURLToPath(new URL("./src", import.meta.url)),
      },
    },
    server: {
      fs: {
        allow: [fileURLToPath(new URL("..", import.meta.url))],
      },
      proxy: {
        "/api": {
          target: env.VITE_PROXY_TARGET || "http://127.0.0.1:8000",
          changeOrigin: true,
        },
      },
    },
    test: {
      environment: "happy-dom",
      setupFiles: ["./tests/setup.ts"],
      css: true,
      globals: true,
      include: ["tests/unit/**/*.spec.ts"],
    },
  };
});
