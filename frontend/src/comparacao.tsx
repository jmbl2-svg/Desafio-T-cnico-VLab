import { createRoot, type Root } from "react-dom/client";
import { lerRoteiro, type Passo } from "./diferencas.ts";
import "./comparacao.css";

function Roteiro({ passos }: { passos: Passo[] }) {
  return <ol className="roteiro-v2">
    {passos.map(passo => <li key={passo.ordem}>
      <div className="roteiro-numero" aria-hidden="true">{passo.ordem}</div>
      <div className="roteiro-conteudo">
        <h4>{passo.acao}</h4>
        <p className="roteiro-sinal"><strong>Sinal e próxima ação</strong>{passo.sinal_esperado}</p>
        <details><summary>Se falhar</summary><p>{passo.se_falhar}</p></details>
      </div>
    </li>)}
  </ol>;
}

let root: Root | undefined;
document.addEventListener("vlab:comparacao", evento => {
  root?.unmount();
  root = undefined;
  const detalhe = (evento as CustomEvent<{v2: unknown} | null>).detail;
  const alvo = document.getElementById("roteiro-v2-react");
  const passos = lerRoteiro(detalhe?.v2);
  if (alvo && passos.length) {
    root = createRoot(alvo);
    root.render(<Roteiro passos={passos} />);
  }
});
