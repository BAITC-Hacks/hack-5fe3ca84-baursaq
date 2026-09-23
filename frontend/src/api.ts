export async function api<T>(path: string, token = '', options: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api${path}`, {...options, headers: {
    ...(options.body instanceof FormData ? {} : {'Content-Type': 'application/json'}),
    ...(token ? {Authorization: `Bearer ${token}`} : {}), ...options.headers,
  }});
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail));
  return data as T;
}
