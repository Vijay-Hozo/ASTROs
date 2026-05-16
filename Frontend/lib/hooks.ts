/**
 * Custom React Hooks for API Data Fetching
 * Reusable hooks for loading, error handling, and data management
 */

"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { apiClient } from "./api-client";
import type { APIError } from "./api-client";

// ============================================================================
// useApiData: Generic Data Fetching Hook
// ============================================================================

export interface UseApiDataOptions {
  skip?: boolean;
  refetchInterval?: number;
  onError?: (error: APIError) => void;
  onSuccess?: (data: unknown) => void;
}

export function useApiData<T>(
  endpoint: string | null,
  options: UseApiDataOptions = {}
) {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(!!endpoint && !options.skip);
  const [error, setError] = useState<APIError | null>(null);
  const refetchIntervalRef = useRef<NodeJS.Timeout>();

  const fetchData = useCallback(async () => {
    if (!endpoint || options.skip) {
      setData(null);
      setIsLoading(false);
      return;
    }

    try {
      setIsLoading(true);
      setError(null);
      const result = await apiClient.get<T>(endpoint);
      setData(result);
      options.onSuccess?.(result);
    } catch (err) {
      const apiError = err as APIError;
      setError(apiError);
      options.onError?.(apiError);
    } finally {
      setIsLoading(false);
    }
  }, [endpoint, options]);

  useEffect(() => {
    fetchData();

    // Handle refetch interval
    if (options.refetchInterval && options.refetchInterval > 0) {
      refetchIntervalRef.current = setInterval(fetchData, options.refetchInterval);
      return () => {
        if (refetchIntervalRef.current) {
          clearInterval(refetchIntervalRef.current);
        }
      };
    }
  }, [endpoint, fetchData, options.refetchInterval]);

  return { data, isLoading, error, refetch: fetchData };
}

// ============================================================================
// useMutate: Generic Mutation Hook
// ============================================================================

export interface UseMutateOptions<T> {
  onSuccess?: (data: T) => void;
  onError?: (error: APIError) => void;
}

export interface UseMutateResult<T> {
  mutate: (body: unknown) => Promise<T>;
  isLoading: boolean;
  error: APIError | null;
  data: T | null;
  reset: () => void;
}

export function useMutate<T>(
  endpoint: string,
  options: UseMutateOptions<T> = {}
): UseMutateResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<APIError | null>(null);

  const mutate = useCallback(
    async (body: unknown): Promise<T> => {
      try {
        setIsLoading(true);
        setError(null);
        const result = await apiClient.post<T>(endpoint, body);
        setData(result);
        options.onSuccess?.(result);
        return result;
      } catch (err) {
        const apiError = err as APIError;
        setError(apiError);
        options.onError?.(apiError);
        throw apiError;
      } finally {
        setIsLoading(false);
      }
    },
    [endpoint, options]
  );

  const reset = useCallback(() => {
    setData(null);
    setError(null);
    setIsLoading(false);
  }, []);

  return { mutate, isLoading, error, data, reset };
}

// ============================================================================
// useDelete: Delete Mutation Hook
// ============================================================================

export function useDelete<T = null>(
  options: UseMutateOptions<T> = {}
): UseMutateResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<APIError | null>(null);

  const mutate = useCallback(
    async (endpoint: string): Promise<T> => {
      try {
        setIsLoading(true);
        setError(null);
        const result = await apiClient.delete<T>(endpoint);
        setData(result);
        options.onSuccess?.(result as T);
        return result as T;
      } catch (err) {
        const apiError = err as APIError;
        setError(apiError);
        options.onError?.(apiError);
        throw apiError;
      } finally {
        setIsLoading(false);
      }
    },
    [options]
  );

  const reset = useCallback(() => {
    setData(null);
    setError(null);
    setIsLoading(false);
  }, []);

  return { mutate, isLoading, error, data, reset };
}

// ============================================================================
// useUploadFile: File Upload Hook
// ============================================================================

export function useUploadFile<T>(
  endpoint: string,
  options: UseMutateOptions<T> = {}
): UseMutateResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<APIError | null>(null);

  const mutate = useCallback(
    async (file: File): Promise<T> => {
      try {
        setIsLoading(true);
        setError(null);
        const result = await apiClient.uploadFile<T>(endpoint, file);
        setData(result);
        options.onSuccess?.(result);
        return result;
      } catch (err) {
        const apiError = err as APIError;
        setError(apiError);
        options.onError?.(apiError);
        throw apiError;
      } finally {
        setIsLoading(false);
      }
    },
    [endpoint, options]
  );

  const reset = useCallback(() => {
    setData(null);
    setError(null);
    setIsLoading(false);
  }, []);

  return { mutate, isLoading, error, data, reset };
}
