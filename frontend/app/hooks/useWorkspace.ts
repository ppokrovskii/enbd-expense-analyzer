import { useState, useEffect, useCallback } from 'react';
import { setActiveWorkspaceId, API_URL } from '../utils/api';

export interface Workspace {
  id: number;
  user_id: string;
  name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export function useWorkspace() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [activeWorkspace, setActiveWorkspace] = useState<Workspace | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchWorkspaces = useCallback(async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/api/workspaces/`, {
        headers: {
          'X-User-Id': 'default_user',
        },
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch workspaces');
      }
      
      const data = await response.json();
      setWorkspaces(data);
      
      // Find the active workspace
      const active = data.find((w: Workspace) => w.is_active);
      if (active) {
        setActiveWorkspace(active);
        setActiveWorkspaceId(active.id);  // Update global workspace_id for API calls
      }
      
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchActiveWorkspace = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/workspaces/active`, {
        headers: {
          'X-User-Id': 'default_user',
        },
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch active workspace');
      }
      
      const data = await response.json();
      setActiveWorkspace(data);
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      return null;
    }
  }, []);

  const switchWorkspace = useCallback(async (workspaceId: number) => {
    try {
      const response = await fetch(`${API_URL}/api/workspaces/${workspaceId}/activate`, {
        method: 'PUT',
        headers: {
          'X-User-Id': 'default_user',
        },
      });
      
      if (!response.ok) {
        throw new Error('Failed to switch workspace');
      }
      
      const data = await response.json();
      setActiveWorkspace(data);
      setActiveWorkspaceId(data.id);  // Update global workspace_id for API calls
      
      // Refresh the list to update is_active flags
      await fetchWorkspaces();
      
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      return null;
    }
  }, [fetchWorkspaces]);

  const createWorkspace = useCallback(async (name: string) => {
    try {
      const response = await fetch(`${API_URL}/api/workspaces/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Id': 'default_user',
        },
        body: JSON.stringify({ name }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to create workspace');
      }
      
      const data = await response.json();
      
      // Refresh the list
      await fetchWorkspaces();
      
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      return null;
    }
  }, [fetchWorkspaces]);

  const deleteWorkspace = useCallback(async (workspaceId: number) => {
    try {
      const response = await fetch(`${API_URL}/api/workspaces/${workspaceId}`, {
        method: 'DELETE',
        headers: {
          'X-User-Id': 'default_user',
        },
      });
      
      if (!response.ok) {
        throw new Error('Failed to delete workspace');
      }
      
      // Refresh the list
      await fetchWorkspaces();
      
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      return false;
    }
  }, [fetchWorkspaces]);

  const updateWorkspace = useCallback(async (workspaceId: number, name: string) => {
    try {
      const response = await fetch(`${API_URL}/api/workspaces/${workspaceId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Id': 'default_user',
        },
        body: JSON.stringify({ name }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to update workspace');
      }
      
      const data = await response.json();
      
      // Refresh the list
      await fetchWorkspaces();
      
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      return null;
    }
  }, [fetchWorkspaces]);

  useEffect(() => {
    fetchWorkspaces();
  }, [fetchWorkspaces]);

  // Helper to get headers for API calls that include workspace_id
  const getApiHeaders = (): Record<string, string> => {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'X-User-Id': 'default_user',
    };
    
    if (activeWorkspace?.id) {
      headers['X-Workspace-Id'] = String(activeWorkspace.id);
    }
    
    return headers;
  };

  return {
    workspaces,
    activeWorkspace,
    loading,
    error,
    switchWorkspace,
    createWorkspace,
    deleteWorkspace,
    updateWorkspace,
    refresh: fetchWorkspaces,
    getApiHeaders,
  };
}
