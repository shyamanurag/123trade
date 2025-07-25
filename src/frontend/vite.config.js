import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
    plugins: [react()],
    base: '/',
    build: {
        outDir: 'dist',
        emptyOutDir: true,
        sourcemap: false,
        minify: 'esbuild',
        chunkSizeWarningLimit: 1000,
        rollupOptions: {
            output: {
                manualChunks: {
                    vendor: ['react', 'react-dom', 'react-router-dom'],
                    mui: ['@mui/material', '@mui/icons-material'],
                },
                entryFileNames: `assets/[name].[hash].js`,
                chunkFileNames: `assets/[name].[hash].js`,
                assetFileNames: `assets/[name].[hash].[ext]`
            },
        },
        // Optimize for DigitalOcean deployment
        esbuildOptions: {
            drop: ['console', 'debugger'],
        },
    },
    server: {
        port: 5173,
        host: true,
        proxy: {
            '/api': {
                target: 'http://localhost:8000',
                changeOrigin: true,
            },
            '/ws': {
                target: 'ws://localhost:8000',
                ws: true,
            }
        }
    },
    preview: {
        port: 3000,
        host: true
    },
    define: {
        'process.env.VITE_API_URL': JSON.stringify(process.env.VITE_API_URL || 'https://quantumcrypto-l43mb.ondigitalocean.app'),
        'process.env.NODE_ENV': JSON.stringify(process.env.NODE_ENV || 'production')
    }
}) 