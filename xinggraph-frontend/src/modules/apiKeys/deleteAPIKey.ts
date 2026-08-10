import { XingGraphInstance } from "../instances/types";

export default async function deleteApiKey(instance: XingGraphInstance, keyId: string): Promise<void> {
  const response = await instance.fetch(`/auth/api-keys/${keyId}`, { method: "DELETE" });
  if (!response.ok) {
    throw new Error(`Failed to delete API key (${response.status})`);
  }
}
