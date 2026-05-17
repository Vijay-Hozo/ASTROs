/**
 * Production API Client
 * Centralized API layer with fetch wrapper, error handling, retry logic, and typed methods
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
const REQUEST_TIMEOUT = 30000; // 30 seconds
const MAX_RETRIES = 2; // Retry failed requests up to 2 times
const RETRY_DELAY = 1000; // Start with 1 second delay, exponential backoff

// ============================================================================
// Types
// ============================================================================

export interface APIError {
  code: string;
  message: string;
  status: number;
  details?: Record<string, unknown>;
}

export interface APIResponse<T> {
  data?: T;
  error?: APIError;
  success: boolean;
}

export interface XmlTag {
  tag: string;
  xpath: string;
  sample_value: string;
  inferred_type: "numeric" | "date" | "string";
  canonical_field: string | null;
}

// ============================================================================
// Error Handling
// ============================================================================

class APIClientError extends Error implements APIError {
  code: string;
  message: string;
  status: number;
  details?: Record<string, unknown>;

  constructor(code: string, message: string, status: number, details?: Record<string, unknown>) {
    super(message);
    this.code = code;
    this.message = message;
    this.status = status;
    this.details = details;
    this.name = 'APIClientError';
  }
}

function normalizeError(error: unknown): APIError {
  if (error instanceof APIClientError) {
    return {
      code: error.code,
      message: error.message,
      status: error.status,
      details: error.details,
    };
  }

  if (error instanceof TypeError) {
    // Network error or CORS issue
    const message = `Network error: Unable to reach ${API_BASE}. Check that:
• The backend server is running
• The API URL is correct: ${API_BASE}
• Your internet connection is working`;
    
    return {
      code: 'NETWORK_ERROR',
      message,
      status: 0,
    };
  }

  if (error instanceof DOMException && error.name === 'AbortError') {
    // Request timeout
    return {
      code: 'TIMEOUT_ERROR',
      message: `Request timed out after ${REQUEST_TIMEOUT}ms. The server may be slow or unreachable.`,
      status: 0,
    };
  }

  if (error instanceof Error) {
    return {
      code: 'UNKNOWN_ERROR',
      message: error.message,
      status: 500,
    };
  }

  return {
    code: 'UNKNOWN_ERROR',
    message: 'An unknown error occurred',
    status: 500,
  };
}

// ============================================================================
// Request/Response Handling
// ============================================================================

async function fetchWithTimeout(url: string, options: RequestInit = {}): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    return response;
  } finally {
    clearTimeout(timeoutId);
  }
}

/**
 * Execute a request with automatic retry on network/timeout errors
 * Does NOT retry on HTTP errors (4xx, 5xx) to avoid waste
 */
async function fetchWithRetry(
  url: string,
  options: RequestInit = {},
  retryCount = 0
): Promise<Response> {
  try {
    return await fetchWithTimeout(url, options);
  } catch (error) {
    // Network error or timeout
    const isNetworkError = error instanceof TypeError;
    const isAbortError = error instanceof DOMException && error.name === 'AbortError';
    const isRetryable = isNetworkError || isAbortError;

    // Retry on network/timeout errors, but not after max retries
    if (isRetryable && retryCount < MAX_RETRIES) {
      const delayMs = RETRY_DELAY * Math.pow(2, retryCount); // Exponential backoff
      await new Promise((resolve) => setTimeout(resolve, delayMs));
      return fetchWithRetry(url, options, retryCount + 1);
    }

    // Give up and throw
    throw error;
  }
}

async function parseResponse<T>(response: Response): Promise<T> {
  const contentType = response.headers.get('content-type');
  
  if (!response.ok) {
    let errorData: { detail?: string; message?: string; [key: string]: unknown } = {};
    if (contentType?.includes('application/json')) {
      try {
        errorData = await response.json();
      } catch {
        errorData = { detail: response.statusText };
      }
    }

    throw new APIClientError(
      `HTTP_${response.status}`,
      errorData.detail || errorData.message || response.statusText || 'API request failed',
      response.status,
      errorData
    );
  }

  if (!contentType?.includes('application/json')) {
    throw new APIClientError(
      'INVALID_RESPONSE',
      'Server returned non-JSON response',
      response.status
    );
  }

  try {
    return await response.json();
  } catch {
    throw new APIClientError(
      'JSON_PARSE_ERROR',
      'Failed to parse server response',
      response.status
    );
  }
}

// ============================================================================
// Request Logging (Development Only)
// ============================================================================

function logRequest(method: string, url: string, body?: unknown) {
  if (process.env.NODE_ENV === 'development') {
    console.log(`[API] ${method} ${url}`, body ? { body } : '');
  }
}

function logResponse(method: string, url: string, status: number, data: unknown) {
  if (process.env.NODE_ENV === 'development') {
    console.log(`[API] ${method} ${url} - ${status}`, data);
  }
}

function logError(method: string, url: string, error: APIError) {
  console.error(`[API ERROR] ${method} ${url} - ${error.status}`, error.message);
}

// ============================================================================
// API Client
// ============================================================================

export const apiClient = {
  /**
   * GET request
   */
  async get<T = unknown>(endpoint: string): Promise<T> {
    const url = `${API_BASE}${endpoint}`;
    logRequest('GET', url);

    try {
      const response = await fetchWithRetry(url, {
        method: 'GET',
      });

      const data = await parseResponse<T>(response);
      logResponse('GET', url, response.status, data);
      return data;
    } catch (error) {
      const apiError = normalizeError(error);
      logError('GET', url, apiError);
      throw apiError;
    }
  },

  /**
   * POST request
   */
  async post<T = unknown>(endpoint: string, body: unknown): Promise<T> {
    const url = `${API_BASE}${endpoint}`;
    logRequest('POST', url, body);

    try {
      const response = await fetchWithRetry(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      });

      const data = await parseResponse<T>(response);
      logResponse('POST', url, response.status, data);
      return data;
    } catch (error) {
      const apiError = normalizeError(error);
      logError('POST', url, apiError);
      throw apiError;
    }
  },

  /**
   * DELETE request
   */
  async put<T = unknown>(endpoint: string, body: unknown): Promise<T> {
    const url = `${API_BASE}${endpoint}`;
    logRequest('PUT', url, body);

    try {
      const response = await fetchWithRetry(url, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      });

      const data = await parseResponse<T>(response);
      logResponse('PUT', url, response.status, data);
      return data;
    } catch (error) {
      const apiError = normalizeError(error);
      logError('PUT', url, apiError);
      throw apiError;
    }
  },

  /**
   * DELETE request
   */
  async delete<T = unknown>(endpoint: string): Promise<T | null> {
    const url = `${API_BASE}${endpoint}`;
    logRequest('DELETE', url);

    try {
      const response = await fetchWithRetry(url, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      // Handle 204 No Content
      if (response.status === 204) {
        logResponse('DELETE', url, 204, null);
        return null;
      }

      const data = await parseResponse<T>(response);
      logResponse('DELETE', url, response.status, data);
      return data;
    } catch (error) {
      const apiError = normalizeError(error);
      logError('DELETE', url, apiError);
      throw apiError;
    }
  },

  /**
   * File upload (multipart form data)
   */
  async uploadFile<T = unknown>(endpoint: string, file: File): Promise<T> {
    const url = `${API_BASE}${endpoint}`;
    logRequest('POST (multipart)', url, { filename: file.name, size: file.size });

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetchWithTimeout(url, {
        method: 'POST',
        body: formData,
        // Note: Don't set Content-Type header; browser will set it with boundary
      });

      const data = await parseResponse<T>(response);
      logResponse('POST (multipart)', url, response.status, data);
      return data;
    } catch (error) {
      const apiError = normalizeError(error);
      logError('POST (multipart)', url, apiError);
      throw apiError;
    }
  },

  /**
   * Retry helper for transient failures
   */
  async withRetry<T>(
    fn: () => Promise<T>,
    maxRetries: number = 3,
    delayMs: number = 1000
  ): Promise<T> {
    let lastError: unknown;

    for (let attempt = 0; attempt < maxRetries; attempt++) {
      try {
        return await fn();
      } catch (error) {
        lastError = error;
        if (attempt < maxRetries - 1) {
          await new Promise(resolve => setTimeout(resolve, delayMs * Math.pow(2, attempt)));
        }
      }
    }

    throw lastError;
  },
};

// ============================================================================
// Health Check Helper
// ============================================================================

export async function checkAPIHealth(): Promise<boolean> {
  try {
    const response = await apiClient.get('/health');
    return !!response;
  } catch {
    return false;
  }
}

const API_BASE_URL = API_BASE;

export async function uploadSampleXml(file: File): Promise<{
  tags: XmlTag[];
  known_tags: XmlTag[];
  unknown_tags: XmlTag[];
  total: number;
}> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/upload-sample-xml`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to parse XML file.");
  }

  return response.json();
}

export async function resolveTag(rawTag: string, canonicalField: string): Promise<void> {
  await fetch(`${API_BASE_URL}/resolve-tag`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ raw_tag: rawTag, canonical_field: canonicalField }),
  });
}
