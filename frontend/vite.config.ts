import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  return {
    plugins: [react()],
    define: {
      __APP_VERSION__: JSON.stringify(env.npm_package_version),
    },
    server: {
      port: 5173,
    },
    build: {
      outDir: 'dist',
    },
  };
});
