import type { XingGraphInstance } from "@/modules/instances/types";

export interface PromptsContent {
  graph_default: string;
  graph_structured_doc: string;
  answer_default: string;
  answer_structured_doc: string;
}

export default async function getPrompts(
  instance: XingGraphInstance,
): Promise<PromptsContent> {
  const response = await instance.fetch("/configuration/get_prompts");
  if (!response.ok) {
    throw new Error(`Failed to load prompts: ${response.status}`);
  }
  const data = await response.json();
  return {
    graph_default: data.graph_default ?? "",
    graph_structured_doc: data.graph_structured_doc ?? "",
    answer_default: data.answer_default ?? "",
    answer_structured_doc: data.answer_structured_doc ?? "",
  };
}
