import { XingGraphInstance } from "@/modules/instances/types";

export default function getDatasetGraph(dataset: { id: string }, instance: XingGraphInstance) {
  return instance.fetch(`/v1/datasets/${dataset.id}/graph`)
      .then((response) => {
        if (!response.ok) throw new Error(`graph fetch failed: ${response.status}`);
        return response.json();
      });
}
