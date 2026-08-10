import { XingGraphInstance } from "../instances/types";

export default function createNotebook(notebookName: string, instance: XingGraphInstance) {
  return instance.fetch("/v1/notebooks/", {
    body: JSON.stringify({ name: notebookName }),
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
  }).then((response) => response.json());
}
