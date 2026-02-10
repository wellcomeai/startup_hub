/**
 * API Client Module for AI Community Club
 *
 * Provides authenticated HTTP methods and token management
 * for communicating with the backend REST API.
 */

'use strict';

const API_BASE = window.location.origin + '/api';
const TOKEN_KEY = 'token';
const USER_KEY = 'user';

// ---------------------------------------------------------------------------
// Token & user helpers
// ---------------------------------------------------------------------------

const getToken = () => localStorage.getItem(TOKEN_KEY);

const setToken = (token) => localStorage.setItem(TOKEN_KEY, token);

const removeToken = () => localStorage.removeItem(TOKEN_KEY);

const getUser = () => {
    try {
        const raw = localStorage.getItem(USER_KEY);
        return raw ? JSON.parse(raw) : null;
    } catch {
        return null;
    }
};

const setUser = (user) => localStorage.setItem(USER_KEY, JSON.stringify(user));

const removeUser = () => localStorage.removeItem(USER_KEY);

const isAuthenticated = () => !!getToken();

/**
 * Clear all auth data and redirect to the landing page.
 */
const logout = () => {
    removeToken();
    removeUser();
    window.location.href = '/static/index.html';
};

// ---------------------------------------------------------------------------
// Core fetch wrapper
// ---------------------------------------------------------------------------

/**
 * Wrapper around the native fetch API.
 *
 * - Prepends `API_BASE` to every endpoint.
 * - Attaches the Authorization header when a token is present.
 * - Automatically parses JSON responses.
 * - On 401 responses clears the stored credentials and redirects to index.
 *
 * @param {string} endpoint - Path relative to the API root (e.g. "/auth/login").
 * @param {RequestInit} [options={}] - Standard fetch options.
 * @returns {Promise<any>} Parsed JSON body.
 */
const fetchAPI = async (endpoint, options = {}) => {
    const url = `${API_BASE}${endpoint}`;

    const headers = {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
    };

    const token = getToken();
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const config = {
        ...options,
        headers,
    };

    const response = await fetch(url, config);

    // Handle authentication failures globally
    if (response.status === 401) {
        removeToken();
        removeUser();
        window.location.href = '/static/index.html';
        // Return a never-resolving promise so callers do not continue
        return new Promise(() => {});
    }

    // Attempt to parse the response body as JSON.
    // Some endpoints (e.g. 204 No Content) may have an empty body.
    let data;
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
        data = await response.json();
    } else {
        data = await response.text();
    }

    if (!response.ok) {
        const message =
            (typeof data === 'object' && data !== null && data.detail) ||
            `Request failed with status ${response.status}`;
        const error = new Error(message);
        error.status = response.status;
        error.data = data;
        throw error;
    }

    return data;
};

// ---------------------------------------------------------------------------
// Convenience methods
// ---------------------------------------------------------------------------

const api = {
    /**
     * Perform a GET request.
     * @param {string} endpoint
     * @returns {Promise<any>}
     */
    get: (endpoint) => fetchAPI(endpoint, { method: 'GET' }),

    /**
     * Perform a POST request with a JSON body.
     * @param {string} endpoint
     * @param {any} data
     * @returns {Promise<any>}
     */
    post: (endpoint, data) =>
        fetchAPI(endpoint, {
            method: 'POST',
            body: JSON.stringify(data),
        }),

    /**
     * Perform a PUT request with a JSON body.
     * @param {string} endpoint
     * @param {any} data
     * @returns {Promise<any>}
     */
    put: (endpoint, data) =>
        fetchAPI(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data),
        }),

    /**
     * Perform a DELETE request.
     * @param {string} endpoint
     * @returns {Promise<any>}
     */
    delete: (endpoint) => fetchAPI(endpoint, { method: 'DELETE' }),
};
