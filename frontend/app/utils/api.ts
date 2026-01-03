/**
 * API utility functions for making authenticated requests.
 * Handles user and person identification headers automatically.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Store active person_id globally (updated by PersonSwitcher)
let activePersonId: number | null = null;

// Initialize from localStorage on load
if (typeof window !== 'undefined') {
  const stored = localStorage.getItem('activePersonId');
  if (stored) {
    activePersonId = parseInt(stored, 10);
  }
}

/**
 * Set the active person ID (called when switching persons)
 * Dispatches a custom event so components can re-fetch data
 */
export function setActivePersonId(personId: number | null): void {
  const previousPersonId = activePersonId;
  activePersonId = personId;
  if (typeof window !== 'undefined') {
    if (personId !== null) {
      localStorage.setItem('activePersonId', String(personId));
    } else {
      localStorage.removeItem('activePersonId');
    }
    
    // Dispatch event if person changed (so components can re-fetch)
    if (previousPersonId !== personId) {
      window.dispatchEvent(new CustomEvent('personChanged', { detail: { personId } }));
    }
  }
}

/**
 * Get the active person ID
 */
export function getActivePersonId(): number | null {
  return activePersonId;
}

/**
 * Get headers for API calls including user and person identification
 */
export function getApiHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-User-Id': 'default_user', // TODO: Get from auth context in production
  };
  
  if (activePersonId !== null) {
    headers['X-Person-Id'] = String(activePersonId);
  }
  
  return headers;
}

/**
 * Make a fetch request with proper headers
 */
export async function fetchApi(endpoint: string, options: RequestInit = {}): Promise<Response> {
  const headers = getApiHeaders();
  
  // Merge with any headers passed in options (but don't override Content-Type for FormData)
  const isFormData = options.body instanceof FormData;
  const mergedHeaders: Record<string, string> = {
    ...headers,
    ...(options.headers as Record<string, string> || {}),
  };
  
  // Remove Content-Type for FormData (browser sets it automatically with boundary)
  if (isFormData) {
    delete mergedHeaders['Content-Type'];
  }
  
  return fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: mergedHeaders,
  });
}

/**
 * Helper to build query string from params
 */
export function buildQueryString(params: Record<string, any>): string {
  const searchParams = new URLSearchParams();
  
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') {
      if (Array.isArray(value)) {
        value.forEach(v => searchParams.append(key, String(v)));
      } else {
        searchParams.append(key, String(value));
      }
    }
  }
  
  const queryString = searchParams.toString();
  return queryString ? `?${queryString}` : '';
}

