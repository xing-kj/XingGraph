import { XingGraphInstance } from "../instances/types";

export default function deleteNotebook(notebookId: string, instance: XingGraphInstance) {
  return instance.fetch(`/v1/notebooks/${notebookId}`, {
    method: "DELETE",
  });
}
