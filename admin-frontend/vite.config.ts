import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': '/src',
    },
  },
  esbuild: {
    drop: ['console', 'debugger'],
  },
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': {
        // Align with Docker stack, which exposes FastAPI on port 8000.
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
        ws: true, // Enable WebSocket proxying
        timeout: 30000, // 30 second timeout
        proxyTimeout: 30000,
        configure: (proxy, options) => { // cast to any for event listeners
          (proxy as any).on('error', (err, req, res) => {
            console.error('❌ Proxy error:', err.message);
            // Send error response if headers not sent
            if (!res.headersSent) {
              res.writeHead(502, { 'Content-Type': 'application/json' });
              res.end(JSON.stringify({ 
                error: 'Proxy Error', 
                message: 'Backend connection failed. Please ensure the API server is running on port 8000.',
                details: err.message 
              }));
            }
          });
          (proxy as any).on('proxyReq', (proxyReq, req, res) => {
            console.log('📤 Sending Request to the Target:', req.method, req.url);
            // Set keep-alive headers
            proxyReq.setHeader('Connection', 'keep-alive');
          });
          (proxy as any).on('proxyRes', (proxyRes, req, res) => {
            console.log('📥 Received Response from the Target:', proxyRes.statusCode, req.url);
          });
          (proxy as any).on('proxyReqWs', (proxyReq, req, socket, options, head) => {
            console.log('🔌 WebSocket proxy request');
          });
          (proxy as any).on('close', (res, socket, head) => {
            console.log('🔌 WebSocket connection closed');
          });
        },
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          'vendor-antd': ['antd', '@ant-design/icons'],
          'vendor-utils': ['axios', 'date-fns', 'xlsx'],
          'vendor-charts': ['recharts'],
        },
      },
    },
  },
})
