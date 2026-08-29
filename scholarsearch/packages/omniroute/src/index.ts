import { type TaskType, selectModel, type TaskClassification } from "./router.js";
import { callAnthropic, type LLMResponse as AnthropicResponse } from "./providers/anthropic.js";
import { callOpenAI, type LLMResponse as OpenAIResponse } from "./providers/openai.js";

export type LLMResponse = AnthropicResponse | OpenAIResponse;

// ============================================
// OmniRoute Main Interface
// ============================================

export interface OmniRouteConfig {
  preferProvider?: "anthropic" | "openai";
  fallbackEnabled?: boolean;
}

export class OmniRoute {
  private config: OmniRouteConfig;

  constructor(config?: OmniRouteConfig) {
    this.config = {
      preferProvider: config?.preferProvider ?? "anthropic",
      fallbackEnabled: config?.fallbackEnabled ?? true,
    };
  }

  /**
   * Route a task to the appropriate LLM provider and model.
   */
  async route(opts: {
    taskType: TaskType;
    system?: string;
    userMessage: string;
    maxTokens?: number;
    temperature?: number;
    jsonMode?: boolean;
    providerOverride?: "anthropic" | "openai";
  }): Promise<LLMResponse> {
    const classification = selectModel(opts.taskType, opts.providerOverride);

    try {
      if (classification.provider === "anthropic") {
        return await callAnthropic({
          model: classification.model,
          system: opts.system,
          messages: [{ role: "user", content: opts.userMessage }],
          maxTokens: opts.maxTokens,
          temperature: opts.temperature,
        });
      } else {
        return await callOpenAI({
          model: classification.model,
          system: opts.system,
          messages: [{ role: "user", content: opts.userMessage }],
          maxTokens: opts.maxTokens,
          temperature: opts.temperature,
          responseFormat: opts.jsonMode ? { type: "json_object" } : undefined,
        });
      }
    } catch (error) {
      if (this.config.fallbackEnabled) {
        return this.fallback(opts, classification, error);
      }
      throw error;
    }
  }

  /**
   * Fallback to alternative provider on error.
   */
  private async fallback(
    opts: Parameters<OmniRoute["route"]>[0],
    originalClassification: { provider: string; model: string },
    originalError: unknown,
  ): Promise<LLMResponse> {
    const fallbackProvider = originalClassification.provider === "anthropic"
      ? "openai"
      : "anthropic";

    const fallbackClassification = selectModel(opts.taskType, fallbackProvider);

    try {
      if (fallbackClassification.provider === "anthropic") {
        return await callAnthropic({
          model: fallbackClassification.model,
          system: opts.system,
          messages: [{ role: "user", content: opts.userMessage }],
          maxTokens: opts.maxTokens,
          temperature: opts.temperature,
        });
      } else {
        return await callOpenAI({
          model: fallbackClassification.model,
          system: opts.system,
          messages: [{ role: "user", content: opts.userMessage }],
          maxTokens: opts.maxTokens,
          temperature: opts.temperature,
          responseFormat: opts.jsonMode ? { type: "json_object" } : undefined,
        });
      }
    } catch (fallbackError) {
      // Both providers failed
      throw new Error(
        `All LLM providers failed. Original: ${originalError}. Fallback: ${fallbackError}`,
      );
    }
  }
}

// ============================================
// Convenience Methods
// ============================================

export async function expandQuery(
  rawQuery: string,
  omniRoute?: OmniRoute,
): Promise<string> {
  const route = omniRoute ?? new OmniRoute();

  const response = await route.route({
    taskType: "query_expansion",
    system: `You are an academic search query expander. Given a natural-language research question, extract:
1. Key concepts (noun phrases)
2. Synonyms and related terms
3. Boolean search variants
4. For biomedical queries: MeSH terms

Return ONLY a JSON object with these fields:
{
  "concepts": ["concept1", "concept2"],
  "synonyms": ["synonym1", "synonym2"],
  "mesh_terms": ["MeSH Term 1", "MeSH Term 2"],
  "boolean_variants": ["query variant 1", "query variant 2"]
}`,
    userMessage: rawQuery,
    jsonMode: true,
  });

  return response.content;
}

export async function extractPICO(
  abstract: string,
  omniRoute?: OmniRoute,
): Promise<string> {
  const route = omniRoute ?? new OmniRoute();

  const response = await route.route({
    taskType: "pico_extraction",
    system: `You are a clinical research PICO extractor. Given a paper abstract, extract:
- Population (P): age, gender, condition, setting
- Intervention (I): treatment, exposure, diagnostic test
- Comparison (C): control, comparator
- Outcome (O): primary and secondary outcomes
- Study design: RCT, cohort, case-control, etc.
- Country/region of study (if mentioned)
- Sample size

Return ONLY a JSON object:
{
  "population": "...",
  "intervention": "...",
  "comparison": "...",
  "outcome": "...",
  "study_design": "...",
  "country": "...",
  "sample_size": "...",
  "age_range": "...",
  "setting": "..."
}

Mark the response as heuristic (not ground truth).`,
    userMessage: abstract,
    jsonMode: true,
  });

  return response.content;
}

export async function explainRelevance(
  query: string,
  paperTitle: string,
  paperAbstract: string,
  omniRoute?: OmniRoute,
): Promise<string> {
  const route = omniRoute ?? new OmniRoute();

  const response = await route.route({
    taskType: "relevance_explanation",
    system: `You are an academic relevance explainer. Given a search query and a paper, write 1-3 concise sentences explaining why this paper matches the query. Be factual and specific. Do not exaggerate the connection.`,
    userMessage: `Query: ${query}\n\nPaper: ${paperTitle}\n\nAbstract: ${paperAbstract}`,
    maxTokens: 256,
  });

  return response.content;
}

// Re-export types
export type { TaskType, TaskComplexity, TaskClassification } from "./router.js";
export type { LLMResponse as AnthropicLLMResponse } from "./providers/anthropic.js";
export type { LLMResponse as OpenAILLMResponse } from "./providers/openai.js";
