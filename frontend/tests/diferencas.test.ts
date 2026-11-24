import { strict as assert } from "node:assert";
import { test } from "node:test";
import { lerRoteiro } from "../src/diferencas.ts";

test("preserva a ordem e os sinais dos passos recebidos pela API", () => {
  const passo = { ordem: 1, acao: "Confira o envio.", sinal_esperado: "Concluído", se_falhar: "Informe o status." };
  assert.deepEqual(lerRoteiro({ passos: [passo, { ...passo, ordem: 2 }] }).map(p => p.ordem), [1, 2]);
});

test("mantém o renderizador original para respostas sem passos", () => {
  assert.deepEqual(lerRoteiro({ hipoteses: ["Envio pendente."] }), []);
  assert.deepEqual(lerRoteiro({ passos: [null, { ordem: 1 }] }), []);
});
