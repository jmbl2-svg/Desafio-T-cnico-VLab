export type Passo = { ordem: number; acao: string; sinal_esperado: string; se_falhar: string };

export function lerRoteiro(saida: unknown): Passo[] {
  if (!saida || typeof saida !== "object" || !("passos" in saida) || !Array.isArray(saida.passos)) return [];
  return saida.passos.filter((passo): passo is Passo => (
    passo && typeof passo.ordem === "number" &&
    typeof passo.acao === "string" && typeof passo.sinal_esperado === "string" &&
    typeof passo.se_falhar === "string"
  ));
}
