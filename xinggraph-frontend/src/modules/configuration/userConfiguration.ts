import type { XingGraphInstance } from "@/modules/instances/types";
import type { GraphModel } from "@/modules/graphModels/types";

export interface UserConfiguration {
  name: string;
  config: object;
}

interface UserConfigurationResponse {
  name: string;
  configuration: object;
}

const MEMORY_SETTINGS_CONFIG_NAME = "memory-settings";
const GRAPH_MODELS_CONFIG_NAME = "graph-models";

export type CustomPromptsMap = Record<string, string>;
export type PromptAssignmentsMap = Record<string, string>;
export type OntologyAssignmentsMap = Record<string, string>;
export type ChunkerAssignmentsMap = Record<string, string>;
export type AnswerPromptAssignmentsMap = Record<string, string>;
export type AnswerCustomPromptsMap = Record<string, string>;

export interface GraphModelsConfig {
  models: GraphModel[];
  customPrompts?: CustomPromptsMap;
  promptAssignments?: PromptAssignmentsMap;
  ontologyAssignments?: OntologyAssignmentsMap;
  chunkerAssignments?: ChunkerAssignmentsMap;
  answerPromptAssignments?: AnswerPromptAssignmentsMap;
  answerCustomPrompts?: AnswerCustomPromptsMap;
  outdatedDatasets?: string[];
}

function emptyGraphModelsConfig(): GraphModelsConfig {
  return {
    models: [],
    customPrompts: {},
    promptAssignments: {},
    ontologyAssignments: {},
    chunkerAssignments: {},
    answerPromptAssignments: {},
    answerCustomPrompts: {},
    outdatedDatasets: [],
  };
}

async function getUserConfigurations(
  instance: XingGraphInstance,
): Promise<UserConfiguration[]> {
  try {
    const response = await instance.fetch("/configuration/get_user_configuration/");
    if (!response.ok) return [];
    const data = await response.json();
    if (!Array.isArray(data)) return [];
    return data.map((item: UserConfigurationResponse) => ({
      name: item.name,
      config: item.configuration,
    }));
  } catch {
    return [];
  }
}

async function storeUserConfiguration(
  instance: XingGraphInstance,
  name: string,
  config: object,
): Promise<void> {
  const response = await instance.fetch("/configuration/store_user_configuration", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, config }),
  });

  if (!response.ok) {
    throw new Error(`Config store failed: ${response.status}`);
  }
}

async function safeUpdateConfig(
  instance: XingGraphInstance,
  name: string,
  config: object,
): Promise<void> {
  await storeUserConfiguration(instance, name, config);
}

export async function syncMemorySettings(
  instance: XingGraphInstance,
  settings: object,
): Promise<void> {
  await safeUpdateConfig(instance, MEMORY_SETTINGS_CONFIG_NAME, settings);
}

export async function loadMemorySettingsFromBackend(
  instance: XingGraphInstance,
): Promise<object | null> {
  const all = await getUserConfigurations(instance);
  const entry = all.find((config) => config.name === MEMORY_SETTINGS_CONFIG_NAME);
  return entry?.config ?? null;
}

export async function syncGraphModels(
  instance: XingGraphInstance,
  models: GraphModel[],
): Promise<void> {
  const existingConfig = await loadGraphModelsConfig(instance);
  await safeUpdateConfig(instance, GRAPH_MODELS_CONFIG_NAME, {
    models,
    customPrompts: existingConfig.customPrompts ?? {},
    promptAssignments: existingConfig.promptAssignments ?? {},
    ontologyAssignments: existingConfig.ontologyAssignments ?? {},
    chunkerAssignments: existingConfig.chunkerAssignments ?? {},
    answerPromptAssignments: existingConfig.answerPromptAssignments ?? {},
    answerCustomPrompts: existingConfig.answerCustomPrompts ?? {},
    outdatedDatasets: existingConfig.outdatedDatasets ?? [],
  });
}

export async function loadGraphModelsConfig(
  instance: XingGraphInstance,
): Promise<GraphModelsConfig> {
  const all = await getUserConfigurations(instance);
  const entry = all.find((config) => config.name === GRAPH_MODELS_CONFIG_NAME);
  if (!entry?.config) return emptyGraphModelsConfig();

  const config = entry.config as GraphModelsConfig;
  return {
    models: config.models ?? [],
    customPrompts: config.customPrompts ?? {},
    promptAssignments: config.promptAssignments ?? {},
    ontologyAssignments: config.ontologyAssignments ?? {},
    chunkerAssignments: config.chunkerAssignments ?? {},
    answerPromptAssignments: config.answerPromptAssignments ?? {},
    answerCustomPrompts: config.answerCustomPrompts ?? {},
    outdatedDatasets: config.outdatedDatasets ?? [],
  };
}

export async function loadGraphModelsFromBackend(
  instance: XingGraphInstance,
): Promise<GraphModel[]> {
  const config = await loadGraphModelsConfig(instance);
  return config.models;
}

function buildGraphModelsPayload(config: GraphModelsConfig): object {
  return {
    models: config.models,
    customPrompts: config.customPrompts ?? {},
    promptAssignments: config.promptAssignments ?? {},
    ontologyAssignments: config.ontologyAssignments ?? {},
    chunkerAssignments: config.chunkerAssignments ?? {},
    answerPromptAssignments: config.answerPromptAssignments ?? {},
    answerCustomPrompts: config.answerCustomPrompts ?? {},
    outdatedDatasets: config.outdatedDatasets ?? [],
  };
}

export async function assignGraphModelToDataset(
  instance: XingGraphInstance,
  datasetId: string,
  modelId: string | null,
): Promise<void> {
  const config = await loadGraphModelsConfig(instance);

  for (const model of config.models) {
    if (model.assignedDatasets) {
      model.assignedDatasets = model.assignedDatasets.filter((id) => id !== datasetId);
    }
  }

  if (modelId !== null) {
    const target = config.models.find((model) => model.id === modelId);
    if (target) {
      target.assignedDatasets = [...(target.assignedDatasets ?? []), datasetId];
    }
  }

  const outdatedDatasets = new Set(config.outdatedDatasets ?? []);
  outdatedDatasets.add(datasetId);
  config.outdatedDatasets = [...outdatedDatasets];
  await safeUpdateConfig(instance, GRAPH_MODELS_CONFIG_NAME, buildGraphModelsPayload(config));
}

export async function clearDatasetOutdated(
  instance: XingGraphInstance,
  datasetId: string,
): Promise<void> {
  const config = await loadGraphModelsConfig(instance);
  config.outdatedDatasets = (config.outdatedDatasets ?? []).filter((id) => id !== datasetId);
  await safeUpdateConfig(instance, GRAPH_MODELS_CONFIG_NAME, buildGraphModelsPayload(config));
}

export function findModelForDataset(
  models: GraphModel[],
  datasetId: string,
): GraphModel | null {
  return models.find((model) => model.assignedDatasets?.includes(datasetId)) ?? null;
}

export function findPromptForDataset(
  assignments: PromptAssignmentsMap,
  datasetId: string,
): string | null {
  return assignments[datasetId] ?? null;
}

export async function assignPromptToDataset(
  instance: XingGraphInstance,
  datasetId: string,
  promptName: string | null,
): Promise<void> {
  const config = await loadGraphModelsConfig(instance);
  const assignments = { ...(config.promptAssignments ?? {}) };

  if (promptName) {
    assignments[datasetId] = promptName;
  } else {
    delete assignments[datasetId];
  }

  config.promptAssignments = assignments;
  const outdatedDatasets = new Set(config.outdatedDatasets ?? []);
  outdatedDatasets.add(datasetId);
  config.outdatedDatasets = [...outdatedDatasets];
  await safeUpdateConfig(instance, GRAPH_MODELS_CONFIG_NAME, buildGraphModelsPayload(config));
}

export function findOntologyForDataset(
  assignments: OntologyAssignmentsMap,
  datasetId: string,
): string | null {
  return assignments[datasetId] ?? null;
}

export function findChunkerForDataset(
  assignments: ChunkerAssignmentsMap,
  datasetId: string,
): string | null {
  return assignments[datasetId] ?? null;
}

export async function assignChunkerToDataset(
  instance: XingGraphInstance,
  datasetId: string,
  chunkerName: string | null,
): Promise<void> {
  const config = await loadGraphModelsConfig(instance);
  const assignments = { ...(config.chunkerAssignments ?? {}) };

  if (chunkerName) {
    assignments[datasetId] = chunkerName;
  } else {
    delete assignments[datasetId];
  }

  config.chunkerAssignments = assignments;
  const outdatedDatasets = new Set(config.outdatedDatasets ?? []);
  outdatedDatasets.add(datasetId);
  config.outdatedDatasets = [...outdatedDatasets];
  await safeUpdateConfig(instance, GRAPH_MODELS_CONFIG_NAME, buildGraphModelsPayload(config));
}

export async function assignOntologyToDataset(
  instance: XingGraphInstance,
  datasetId: string,
  ontologyKey: string | null,
): Promise<void> {
  const config = await loadGraphModelsConfig(instance);
  const assignments = { ...(config.ontologyAssignments ?? {}) };

  if (ontologyKey) {
    assignments[datasetId] = ontologyKey;
  } else {
    delete assignments[datasetId];
  }

  config.ontologyAssignments = assignments;
  const outdatedDatasets = new Set(config.outdatedDatasets ?? []);
  outdatedDatasets.add(datasetId);
  config.outdatedDatasets = [...outdatedDatasets];
  await safeUpdateConfig(instance, GRAPH_MODELS_CONFIG_NAME, buildGraphModelsPayload(config));
}

export async function saveCustomPrompt(
  instance: XingGraphInstance,
  name: string,
  promptText: string,
): Promise<void> {
  const config = await loadGraphModelsConfig(instance);
  config.customPrompts = { ...(config.customPrompts ?? {}), [name]: promptText };
  await safeUpdateConfig(instance, GRAPH_MODELS_CONFIG_NAME, buildGraphModelsPayload(config));
}

export async function deleteCustomPrompt(
  instance: XingGraphInstance,
  name: string,
): Promise<void> {
  const config = await loadGraphModelsConfig(instance);
  const prompts = { ...(config.customPrompts ?? {}) };
  delete prompts[name];
  config.customPrompts = prompts;
  await safeUpdateConfig(instance, GRAPH_MODELS_CONFIG_NAME, buildGraphModelsPayload(config));
}

export async function syncGraphModelsFullConfig(
  instance: XingGraphInstance,
  config: GraphModelsConfig,
): Promise<void> {
  await safeUpdateConfig(instance, GRAPH_MODELS_CONFIG_NAME, buildGraphModelsPayload(config));
}

export function findAnswerPromptForDataset(
  assignments: AnswerPromptAssignmentsMap,
  datasetId: string,
): string | null {
  return assignments[datasetId] ?? null;
}

export async function assignAnswerPromptToDataset(
  instance: XingGraphInstance,
  datasetId: string,
  assignment: string | null,
): Promise<void> {
  const config = await loadGraphModelsConfig(instance);
  const assignments = { ...(config.answerPromptAssignments ?? {}) };

  if (assignment) {
    assignments[datasetId] = assignment;
  } else {
    delete assignments[datasetId];
  }

  config.answerPromptAssignments = assignments;
  await safeUpdateConfig(instance, GRAPH_MODELS_CONFIG_NAME, buildGraphModelsPayload(config));
}

export async function saveAnswerCustomPrompt(
  instance: XingGraphInstance,
  name: string,
  promptText: string,
): Promise<void> {
  const config = await loadGraphModelsConfig(instance);
  config.answerCustomPrompts = { ...(config.answerCustomPrompts ?? {}), [name]: promptText };
  await safeUpdateConfig(instance, GRAPH_MODELS_CONFIG_NAME, buildGraphModelsPayload(config));
}

export async function deleteAnswerCustomPrompt(
  instance: XingGraphInstance,
  name: string,
): Promise<void> {
  const config = await loadGraphModelsConfig(instance);
  const prompts = { ...(config.answerCustomPrompts ?? {}) };
  delete prompts[name];
  config.answerCustomPrompts = prompts;
  await safeUpdateConfig(instance, GRAPH_MODELS_CONFIG_NAME, buildGraphModelsPayload(config));
}
