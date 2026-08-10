import { XingGraphInstance } from "../instances/types";

/**
 * Resolves the current user's id from the local backend directly. Must run
 * client-side (via XingGraphInstance.fetch, which carries the auth cookie) —
 * a Next.js server action can't do this, since the auth cookie is scoped to
 * the backend's own origin (localhost:8000), not the Next.js server.
 */
export default async function getMyUserId(instance: XingGraphInstance): Promise<string | null> {
  try {
    const response = await instance.fetch("/users/me");
    if (!response.ok) return null;
    const data = await response.json();
    return data?.id ?? null;
  } catch {
    return null;
  }
}
