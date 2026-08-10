import { XingGraphInstance } from "./types";

/**
 * Safely fetch JSON from an activity endpoint.
 * Returns the parsed data or a fallback value if the endpoint
 * is unavailable (404, 500, network error).
 */
export async function safeFetchJson<T>(
  instance: XingGraphInstance,
  path: string,
  fallback: T,
): Promise<T> {
  try {
    const response = await instance.fetch(path);
    const data = await response.json();
    return data as T;
  } catch {
    return fallback;
  }
}
