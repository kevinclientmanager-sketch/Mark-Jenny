export const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

class ApiError extends Error {
  constructor(public status: number, message: string, public data?: unknown) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
  if (token) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    ...options,
    headers,
    credentials: 'include',
  });

  if (!response.ok) {
    let errorData: unknown;
    try {
      errorData = await response.json();
    } catch {
      errorData = await response.text();
    }
    throw new ApiError(response.status, errorData as string, errorData);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

export const api = {
  get: <T>(endpoint: string) => request<T>(endpoint, { method: 'GET' }),
  post: <T>(endpoint: string, data: unknown) => request<T>(endpoint, {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  patch: <T>(endpoint: string, data: unknown) => request<T>(endpoint, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  delete: <T>(endpoint: string) => request<T>(endpoint, { method: 'DELETE' }),
  put: <T>(endpoint: string, data: unknown) => request<T>(endpoint, {
    method: 'PUT',
    body: JSON.stringify(data),
  }),
};

export { ApiError };
