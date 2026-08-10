import { XingGraphInstance } from "../instances/types";

export default function getNotebooks(instance: XingGraphInstance) {
  return instance.fetch("/v1/notebooks/", {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  }).then((response) => response.json());
}
