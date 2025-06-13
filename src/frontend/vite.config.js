import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
    plugins: [react()],
    base: '/',
    build: {
        outDir: 'dist',
        emptyOutDir: true,
        sourcemap: false,
        minify: true,
        chunkSizeWarningLimit: 1000,
        rollupOptions: {
            output: {
                manualChunks: {
                    vendor: ['react', 'react-dom', 'react-router-dom'],
                    mui: ['@mui/material', '@mui/icons-material'],
                },
            },
        },
        // Optimize for DigitalOcean deployment
        terserOptions: {
            compress: {
                drop_console: true,
                drop_debugger: true,
            },
        },
    },
    server: {
        port: 3000,
        host: true,
        proxy: {
            '/api': {
                target: process.env.VITE_API_URL || 'https://algoauto-jd32t.ondigitalocean.app',
                changeOrigin: true,
                secure: true
            },
            '/ws': {
                target: process.env.VITE_API_URL?.replace('https', 'wss') || 'wss://algoauto-jd32t.ondigitalocean.app',
                ws: true,
                changeOrigin: true,
                secure: true
            }
        }
    },
    preview: {
        port: 3000,
        host: true
    },
    define: {
        'process.env.VITE_API_URL': JSON.stringify(process.env.VITE_API_URL || 'https://algoauto-jd32t.ondigitalocean.app'),
        'process.env.NODE_ENV': JSON.stringify(process.env.NODE_ENV || 'production')
    }
}) 