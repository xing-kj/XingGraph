import { XingGraphInstance } from "../instances/types";

export default function getDatasets(instance: XingGraphInstance) {
  return instance.fetch("/v1/datasets/", {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  }).then((response) => response.json());
}
