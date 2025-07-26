import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
    plugins: [react()],
    define: {
        'process.env': process.env
    },
    server: {
        port: 3000,
        host: true,
        proxy: {
            '/api': {
                target: process.env.VITE_API_URL || 'http://localhost:8000',
                changeOrigin: true,
                secure: false
            },
            '/ws': {
                target: process.env.VITE_WS_URL || 'ws://localhost:8000',
                ws: true,
                changeOrigin: true
            }
        }
    },
    build: {
        outDir: 'dist',
        sourcemap: true,
        rollupOptions: {
            output: {
                manualChunks: {
                    vendor: ['react', 'react-dom'],
                    charts: ['chart.js', 'react-chartjs-2', 'recharts'],
                    ui: ['framer-motion', 'lucide-react']
                }
            }
        }
    },
    optimizeDeps: {
        include: ['react', 'react-dom', 'axios', 'socket.io-client']
    }
}) 