"use client";

import React, { createContext, useContext, useMemo } from 'react';
import { usePerson } from '../hooks/usePerson';
import { API_URL } from '../utils/api';

interface ApiContextValue {
  apiUrl: string;
  getHeaders: () => HeadersInit;
  fetchApi: (endpoint: string, options?: RequestInit) => Promise<Response>;
  personId: number | null;
  userId: string;
}

const ApiContext = createContext<ApiContextValue | null>(null);

export function ApiProvider({ children }: { children: React.ReactNode }) {
  const { activePerson, loading } = usePerson();
  
  const userId = 'default_user'; // TODO: Get from auth context in production
  
  const personId = activePerson?.id ?? null;
  
  const getHeaders = useMemo(() => {
    return (): HeadersInit => {
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
        'X-User-Id': userId,
      };
      
      if (personId !== null) {
        headers['X-Person-Id'] = String(personId);
      }
      
      return headers;
    };
  }, [userId, personId]);
  
  const fetchApi = useMemo(() => {
    return async (endpoint: string, options: RequestInit = {}): Promise<Response> => {
      const headers = getHeaders();
      
      // Merge with any headers passed in options
      const mergedHeaders = {
        ...headers,
        ...(options.headers || {}),
      };
      
      return fetch(`${API_URL}${endpoint}`, {
        ...options,
        headers: mergedHeaders,
      });
    };
  }, [getHeaders]);
  
  const value: ApiContextValue = {
    apiUrl: API_URL,
    getHeaders,
    fetchApi,
    personId,
    userId,
  };
  
  return (
    <ApiContext.Provider value={value}>
      {children}
    </ApiContext.Provider>
  );
}

export function useApi() {
  const context = useContext(ApiContext);
  if (!context) {
    throw new Error('useApi must be used within an ApiProvider');
  }
  return context;
}

// Export a helper to get headers for components that can't use hooks
export function getApiHeaders(personId: number | null, userId: string = 'default_user'): HeadersInit {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    'X-User-Id': userId,
  };
  
  if (personId !== null) {
    headers['X-Person-Id'] = String(personId);
  }
  
  return headers;
}

