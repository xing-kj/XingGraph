import { XingGraphInstance } from "../instances/types";

export default function getDatasetData(datasetId: string, instance: XingGraphInstance) {
  return instance.fetch(`/v1/datasets/${datasetId}/data`)
      .then((response) => response.json());
}
