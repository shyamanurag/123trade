// src/frontend/services/api.ts
// Unified API client with robust error handling and automatic base-URL handling.
// Usage: import { api } from '../services/api'; then api.get('/api/users')

import { format } from 'date-fns';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const BASE_URL: string = ((import.meta as any).env.VITE_API_URL as string) || window.location.origin;

interface RequestOptions extends RequestInit {
    // When true we will skip automatic JSON parsing.
    asText?: boolean;
}

class APIClient {
    private baseUrl: string;

    constructor(baseUrl: string) {
        this.baseUrl = baseUrl.replace(/\/$/, ''); // remove trailing slash
    }

    private async request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
        const url = `${this.baseUrl}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;

        const headers: HeadersInit = {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            ...options.headers,
        };

        // Attach JWT token if present in localStorage
        const token = localStorage.getItem('access_token');
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const response = await fetch(url, { ...options, headers });

        // Attempt to parse JSON only when content-type indicates so
        const contentType = response.headers.get('content-type') || '';

        if (!response.ok) {
            // Parse error body if JSON, else return text
            const errorPayload = contentType.includes('application/json')
                ? await response.json()
                : await response.text();

            const message = (errorPayload && (errorPayload.message || errorPayload.detail)) ||
                `HTTP ${response.status}: ${response.statusText}`;

            throw new Error(message);
        }

        if (options.asText || !contentType.includes('application/json')) {
            // Return raw text (for CSV, HTML etc.)
            return (await response.text()) as unknown as T;
        }

        try {
            return await response.json();
        } catch (e) {
            const raw = await response.text();
            throw new Error(`Invalid JSON received from ${endpoint}: ${raw.slice(0, 100)}`);
        }
    }

    public get<T>(endpoint: string, options?: RequestOptions) {
        return this.request<T>(endpoint, { ...options, method: 'GET' });
    }

    public post<T>(endpoint: string, body?: any, options?: RequestOptions) {
        return this.request<T>(endpoint, {
            ...options,
            method: 'POST',
            body: body !== undefined ? JSON.stringify(body) : undefined,
        });
    }

    public put<T>(endpoint: string, body?: any, options?: RequestOptions) {
        return this.request<T>(endpoint, {
            ...options,
            method: 'PUT',
            body: body !== undefined ? JSON.stringify(body) : undefined,
        });
    }

    public del<T>(endpoint: string, options?: RequestOptions) {
        return this.request<T>(endpoint, { ...options, method: 'DELETE' });
    }
}

export const api = new APIClient(BASE_URL);

// Helper to log API base for debugging
console.info(`[API] Base URL: ${BASE_URL} @ ${format(new Date(), 'yyyy-MM-dd HH:mm:ss')}`); 