/**
 * Synapse Session Authentication & Ticket Manager (Stage 1 Hardened)
 * Obtains and rotates short-lived scoped session tickets.
 * Master API secrets are strictly kept on the server and NEVER exposed to browser clients.
 */

const API_BASE = 'http://127.0.0.1:8000';
const SESSION_KEY = 'synapse_session_token';

let inFlightSessionPromise = null;

export async function getSessionToken(tenantId = 'tenant_primary', forceRefresh = false) {
  if (!forceRefresh) {
    const cached = sessionStorage.getItem(SESSION_KEY);
    if (cached) {
      // Basic client-side check if token has 3 parts (st.payload.sig)
      const parts = cached.split('.');
      if (parts.length === 3 && parts[0] === 'st') {
        try {
          const payload = JSON.parse(atob(parts[1]));
          const nowSec = Math.floor(Date.now() / 1000);
          if (payload.exp && payload.exp - nowSec > 30) {
            return cached;
          }
        } catch (e) {
          // Fall through to re-issue
        }
      }
    }
  }

  if (inFlightSessionPromise) {
    return await inFlightSessionPromise;
  }

  inFlightSessionPromise = (async () => {
    try {
      const res = await fetch(`${API_BASE}/api/auth/session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tenant_id: tenantId })
      });
      if (!res.ok) {
        throw new Error(`Failed to obtain session ticket: HTTP ${res.status}`);
      }
      const data = await res.json();
      const token = data.session_token;
      if (token) {
        sessionStorage.setItem(SESSION_KEY, token);
        return token;
      }
      throw new Error('No session_token in response');
    } finally {
      inFlightSessionPromise = null;
    }
  })();

  return await inFlightSessionPromise;
}

export async function getAuthHeaders(options = {}) {
  const token = await getSessionToken();
  return {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
    ...(options.headers || {})
  };
}

export async function authFetch(endpoint, options = {}) {
  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;
  let token = await getSessionToken();

  let headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
    ...(options.headers || {})
  };

  let res = await fetch(url, { ...options, headers });
  if (res.status === 401) {
    // Session may have expired; refresh once
    sessionStorage.removeItem(SESSION_KEY);
    token = await getSessionToken('tenant_primary', true);
    headers = {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
      ...(options.headers || {})
    };
    res = await fetch(url, { ...options, headers });
  }

  return res;
}

export async function getWebSocketUrl() {
  const token = await getSessionToken();
  return `ws://127.0.0.1:8000/ws/agent?token=${encodeURIComponent(token)}`;
}
