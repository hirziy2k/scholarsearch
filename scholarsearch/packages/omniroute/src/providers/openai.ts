import OpenAI from "openai";

let client: OpenAI | null = null;

function getClient(): OpenAI {
  if (!client) {
    client = new OpenAI({
      apiKey: process.env.OPENAI_API_KEY,
    });
  }
  return client;
}

export interface LLMResponse {
  content: string;
  model: string;
  inputTokens: number;
  outputTokens: number;
  latencyMs: number;
}

export async function callOpenAI(opts: {
  model: string;
  system?: string;
  messages: Array<{ role: "user" | "assistant"; content: string }>;
  maxTokens?: number;
  temperature?: number;
  responseFormat?: { type: "json_object" };
}): Promise<LLMResponse> {
  const start = Date.now();
  const openai = getClient();

  const messages: Array<{ role: "system" | "user" | "assistant"; content: string }> = [];
  if (opts.system) {
    messages.push({ role: "system", content: opts.system });
  }
  messages.push(...opts.messages);

  const response = await openai.chat.completions.create({
    model: opts.model,
    messages,
    max_tokens: opts.maxTokens ?? 1024,
    temperature: opts.temperature ?? 0,
    response_format: opts.responseFormat,
  });

  const choice = response.choices[0];
  const content = choice?.message?.content ?? "";

  return {
    content,
    model: opts.model,
    inputTokens: response.usage?.prompt_tokens ?? 0,
    outputTokens: response.usage?.completion_tokens ?? 0,
    latencyMs: Date.now() - start,
  };
}
