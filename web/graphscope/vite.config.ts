import { defineConfig } from 'vite';

export default defineConfig({
  base: '/LLM-GNN/',
  build: {
    sourcemap: false,
    rollupOptions: { output: { manualChunks: { graph: ['cytoscape'], react: ['react', 'react-dom'] } } },
  },
  server: {
    fs: { strict: true },
    // Only the frontend is served; private research artifacts are outside this root.
    host: '127.0.0.1',
  },
});
