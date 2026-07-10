export type Pricing = {
  inputPerMillion: number;
  cachedInputPerMillion: number;
  outputPerMillion: number;
};

export function calculateCost(pricing: Pricing, usage: any): number {
  const input = Math.max(0, usage?.inputTokens ?? 0);
  const cached = Math.min(input, Math.max(0, usage?.inputTokenDetails?.cacheReadTokens ?? 0));
  const output = Math.max(0, usage?.outputTokens ?? 0);
  return (
    ((input - cached) * pricing.inputPerMillion + cached * pricing.cachedInputPerMillion + output * pricing.outputPerMillion) /
    1_000_000
  );
}
