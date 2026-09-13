import Anthropic from "@anthropic-ai/sdk";

let client: Anthropic | null = null;

function getClient(): Anthropic {
  if (!client) {
    client = new Anthropic({
      apiKey: process.env.ANTHROPIC_API_KEY,
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

export async function callAnthropic(opts: {
  model: string;
  system?: string;
  messages: Array<{ role: "user" | "assistant"; content: string }>;
  maxTokens?: number;
  temperature?: number;
}): Promise<LLMResponse> {
  const start = Date.now();
  const anthropic = getClient();

  const response = await anthropic.messages.create({
    model: opts.model,
    max_tokens: opts.maxTokens ?? 1024,
    temperature: opts.temperature ?? 0,
    system: opts.system,
    messages: opts.messages,
  });

  const textBlock = response.content.find((b) => b.type === "text");
  const content = textBlock?.text ?? "";

  return {
    content,
    model: opts.model,
    inputTokens: response.usage.input_tokens,
    outputTokens: response.usage.output_tokens,
    latencyMs: Date.now() - start,
  };
}
