import { XingGraphInstance } from "../instances/types";

export default function deleteDataset(datasetId: string, instance: XingGraphInstance) {
  return instance.fetch(`/v1/datasets/${datasetId}`, {
    method: "DELETE",
  })
}
