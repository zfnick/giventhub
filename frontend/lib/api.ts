import { User } from "firebase/auth";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

/**
 * Fetch wrapper that auto-attaches a Firebase ID token when a user is provided.
 *
 * Usage:
 *   const { user } = useAuth();
 *   const res = await apiFetch(user, "/api/commit", { method: "POST", body: ... });
 */
export async function apiFetch(
  user: User | null,
  path: string,
  init: Omit<RequestInit, "headers"> & { headers?: Record<string, string>; json?: unknown } = {},
): Promise<Response> {
  const headers: Record<string, string> = { ...(init.headers ?? {}) };

  if (init.json !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  if (user) {
    headers.Authorization = `Bearer ${await user.getIdToken()}`;
  }

  const { json, ...rest } = init;
  return fetch(`${BACKEND_URL}${path}`, {
    ...rest,
    headers,
    body: json !== undefined ? JSON.stringify(json) : rest.body,
  });
}

export { BACKEND_URL };
