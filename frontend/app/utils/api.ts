/**
 * API utility functions for making authenticated requests.
 * Handles user and workspace identification headers automatically.
 */

export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
export const API_BASE_URL = `${API_URL}/api`;
export const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

// Store active workspace_id globally (updated by WorkspaceSwitcher)
let activeWorkspaceId: number | null = null;

// Initialize from localStorage on load
if (typeof window !== 'undefined') {
  const storedWorkspace = localStorage.getItem('activeWorkspaceId');
  if (storedWorkspace) {
    activeWorkspaceId = parseInt(storedWorkspace, 10);
  }
}

/**
 * Set the active workspace ID (called when switching workspaces)
 * Dispatches a custom event so components can re-fetch data
 */
export function setActiveWorkspaceId(workspaceId: number | null): void {
  const previousWorkspaceId = activeWorkspaceId;
  activeWorkspaceId = workspaceId;
  if (typeof window !== 'undefined') {
    if (workspaceId !== null) {
      localStorage.setItem('activeWorkspaceId', String(workspaceId));
    } else {
      localStorage.removeItem('activeWorkspaceId');
    }
    
    // Dispatch event if workspace changed (so components can re-fetch)
    if (previousWorkspaceId !== workspaceId) {
      window.dispatchEvent(new CustomEvent('workspaceChanged', { detail: { workspaceId } }));
    }
  }
}

/**
 * Get the active workspace ID
 */
export function getActiveWorkspaceId(): number | null {
  return activeWorkspaceId;
}

/**
 * Get headers for API calls including user and workspace identification
 */
export function getApiHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-User-Id': 'default_user', // TODO: Get from auth context in production
  };
  
  if (activeWorkspaceId !== null) {
    headers['X-Workspace-Id'] = String(activeWorkspaceId);
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
