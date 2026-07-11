export type Pricing = {
  inputPerMillion: number;
  cachedInputPerMillion: number;
  cacheWritePerMillion?: number;
  outputPerMillion: number;
};

export function calculateCost(pricing: Pricing, usage: any): number {
  const input = Math.max(0, usage?.inputTokens ?? 0);
  const cached = Math.min(input, Math.max(0, usage?.inputTokenDetails?.cacheReadTokens ?? 0));
  const written = Math.min(input - cached, Math.max(0, usage?.inputTokenDetails?.cacheWriteTokens ?? 0));
  const regular = input - cached - written;
  const output = Math.max(0, usage?.outputTokens ?? 0);
  return (
    (regular * pricing.inputPerMillion +
      cached * pricing.cachedInputPerMillion +
      written * (pricing.cacheWritePerMillion ?? pricing.inputPerMillion) +
      output * pricing.outputPerMillion) /
    1_000_000
  );
}
