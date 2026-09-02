// ============================================
// Task Classification
// ============================================

export type TaskType =
  | "query_expansion"
  | "search_strategy"
  | "pico_extraction"
  | "study_classification"
  | "evidence_synthesis"
  | "contradiction_detection"
  | "relevance_explanation"
  | "source_quality_explanation"
  | "demographic_extraction"
  | "query_to_sql"
  | "summary";

export type TaskComplexity = "simple" | "moderate" | "complex";

export interface TaskClassification {
  type: TaskType;
  complexity: TaskComplexity;
  recommendedProvider: "anthropic" | "openai";
  recommendedModel: string;
}

// ============================================
// Routing Rules
// ============================================

const ROUTING_TABLE: Record<TaskType, TaskClassification> = {
  query_expansion: {
    type: "query_expansion",
    complexity: "simple",
    recommendedProvider: "anthropic",
    recommendedModel: "claude-haiku-4-20250414",
  },
  search_strategy: {
    type: "search_strategy",
    complexity: "complex",
    recommendedProvider: "anthropic",
    recommendedModel: "claude-sonnet-4-20250514",
  },
  pico_extraction: {
    type: "pico_extraction",
    complexity: "complex",
    recommendedProvider: "anthropic",
    recommendedModel: "claude-sonnet-4-20250514",
  },
  study_classification: {
    type: "study_classification",
    complexity: "simple",
    recommendedProvider: "anthropic",
    recommendedModel: "claude-haiku-4-20250414",
  },
  evidence_synthesis: {
    type: "evidence_synthesis",
    complexity: "complex",
    recommendedProvider: "anthropic",
    recommendedModel: "claude-sonnet-4-20250514",
  },
  contradiction_detection: {
    type: "contradiction_detection",
    complexity: "complex",
    recommendedProvider: "anthropic",
    recommendedModel: "claude-sonnet-4-20250514",
  },
  relevance_explanation: {
    type: "relevance_explanation",
    complexity: "simple",
    recommendedProvider: "anthropic",
    recommendedModel: "claude-haiku-4-20250414",
  },
  source_quality_explanation: {
    type: "source_quality_explanation",
    complexity: "simple",
    recommendedProvider: "anthropic",
    recommendedModel: "claude-haiku-4-20250414",
  },
  demographic_extraction: {
    type: "demographic_extraction",
    complexity: "moderate",
    recommendedProvider: "anthropic",
    recommendedModel: "claude-haiku-4-20250414",
  },
  query_to_sql: {
    type: "query_to_sql",
    complexity: "moderate",
    recommendedProvider: "anthropic",
    recommendedModel: "claude-sonnet-4-20250514",
  },
  summary: {
    type: "summary",
    complexity: "simple",
    recommendedProvider: "anthropic",
    recommendedModel: "claude-haiku-4-20250414",
  },
};

export function classifyTask(type: TaskType): TaskClassification {
  return ROUTING_TABLE[type]!;
}

export function selectModel(
  type: TaskType,
  providerOverride?: "anthropic" | "openai",
): { provider: string; model: string } {
  const classification = classifyTask(type);
  const provider = providerOverride ?? classification.recommendedProvider;

  if (provider === "openai") {
    return {
      provider: "openai",
      model: classification.complexity === "complex"
        ? "gpt-4o"
        : "gpt-4o-mini",
    };
  }

  return {
    provider: "anthropic",
    model: classification.recommendedModel,
  };
}
