/**
 * Simulate AI thinking latency on the client.
 * Use during Stage 1 wherever a real API call will eventually go.
 */
export function simulateAIThinking(ms = 1800): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Pick a slightly jittered delay so consecutive "regenerate" actions
 * don't feel mechanically identical.
 */
export function jitteredThinking(baseMs = 1800, jitterMs = 600): Promise<void> {
  const delta = (Math.random() - 0.5) * 2 * jitterMs;
  return simulateAIThinking(Math.max(600, baseMs + delta));
}
