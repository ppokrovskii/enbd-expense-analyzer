import { useState, useEffect, useCallback } from 'react';
import { setActivePersonId } from '../utils/api';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface Person {
  id: number;
  user_id: string;
  name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export function usePerson() {
  const [persons, setPersons] = useState<Person[]>([]);
  const [activePerson, setActivePerson] = useState<Person | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPersons = useCallback(async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/api/persons/`, {
        headers: {
          'X-User-Id': 'default_user',
        },
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch persons');
      }
      
      const data = await response.json();
      setPersons(data);
      
      // Find the active person
      const active = data.find((p: Person) => p.is_active);
      if (active) {
        setActivePerson(active);
        setActivePersonId(active.id);  // Update global person_id for API calls
      }
      
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchActivePerson = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/persons/active`, {
        headers: {
          'X-User-Id': 'default_user',
        },
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch active person');
      }
      
      const data = await response.json();
      setActivePerson(data);
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      return null;
    }
  }, []);

  const switchPerson = useCallback(async (personId: number) => {
    try {
      const response = await fetch(`${API_URL}/api/persons/${personId}/activate`, {
        method: 'PUT',
        headers: {
          'X-User-Id': 'default_user',
        },
      });
      
      if (!response.ok) {
        throw new Error('Failed to switch person');
      }
      
      const data = await response.json();
      setActivePerson(data);
      setActivePersonId(data.id);  // Update global person_id for API calls
      
      // Refresh the list to update is_active flags
      await fetchPersons();
      
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      return null;
    }
  }, [fetchPersons]);

  const createPerson = useCallback(async (name: string) => {
    try {
      const response = await fetch(`${API_URL}/api/persons/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Id': 'default_user',
        },
        body: JSON.stringify({ name }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to create person');
      }
      
      const data = await response.json();
      
      // Refresh the list
      await fetchPersons();
      
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      return null;
    }
  }, [fetchPersons]);

  const deletePerson = useCallback(async (personId: number) => {
    try {
      const response = await fetch(`${API_URL}/api/persons/${personId}`, {
        method: 'DELETE',
        headers: {
          'X-User-Id': 'default_user',
        },
      });
      
      if (!response.ok) {
        throw new Error('Failed to delete person');
      }
      
      // Refresh the list
      await fetchPersons();
      
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      return false;
    }
  }, [fetchPersons]);

  const updatePerson = useCallback(async (personId: number, name: string) => {
    try {
      const response = await fetch(`${API_URL}/api/persons/${personId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Id': 'default_user',
        },
        body: JSON.stringify({ name }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to update person');
      }
      
      const data = await response.json();
      
      // Refresh the list
      await fetchPersons();
      
      return data;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      return null;
    }
  }, [fetchPersons]);

  useEffect(() => {
    fetchPersons();
  }, [fetchPersons]);

  // Helper to get headers for API calls that include person_id
  const getApiHeaders = (): Record<string, string> => {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'X-User-Id': 'default_user',
    };
    
    if (activePerson?.id) {
      headers['X-Person-Id'] = String(activePerson.id);
    }
    
    return headers;
  };

  return {
    persons,
    activePerson,
    loading,
    error,
    switchPerson,
    createPerson,
    deletePerson,
    updatePerson,
    refresh: fetchPersons,
    getApiHeaders,
  };
}

