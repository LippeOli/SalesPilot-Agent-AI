#!/usr/bin/env python3
"""
Gera artefatos do diagrama do grafo LangGraph do SalesPilot.

Saídas (na raiz do repositório):
  - salespilot_graph.mmd — Mermaid compatível com mermaid.live / VS Code (não usa a saída
    bruta de draw_mermaid(), que inclui YAML/HTML/classDef e quebra muitos renderizadores)
  - Terminal — diagrama ASCII, se `grandalf` estiver instalado
  - salespilot_graph.png — opcional; usa a API mermaid.ink (requer rede)

Uso:
    python generate_diagram.py
    make diagram
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from salespilot.agent import build_graph  # noqa: E402

# Equivalente ao grafo build_graph(): START → agent ⇄ tools → END.
# Sem frontmatter YAML, sem <p> nas etiquetas e sem classDef (incompatíveis com vários viewers).
MERMAID_COMPAT = """%% SalesPilot — grafo ReAct (LangGraph). Sintaxe compatível com mermaid.live e VS Code.
%% Equivale a: START → agent ⇄ tools → END (sem YAML/HTML/classDef da API draw_mermaid).
flowchart TD
    entrada([Início]) --> agente[agent]
    agente -->|resposta final| saida([Fim])
    agente -->|tool_calls| ferramentas[tools]
    ferramentas --> agente
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Gera diagrama Mermaid/ASCII/PNG do grafo LangGraph.")
    parser.add_argument(
        "--no-png",
        action="store_true",
        help="Não tentar gerar salespilot_graph.png (evita chamadas HTTP).",
    )
    parser.add_argument(
        "--no-ascii",
        action="store_true",
        help="Não imprimir o diagrama ASCII no terminal.",
    )
    args = parser.parse_args()

    compiled = build_graph()
    gx = compiled.get_graph()

    mmd_path = _REPO_ROOT / "salespilot_graph.mmd"
    mmd_path.write_text(MERMAID_COMPAT, encoding="utf-8")
    print(f"OK: {mmd_path}", flush=True)

    if not args.no_ascii:
        print("\n--- Diagrama ASCII ---", flush=True)
        try:
            gx.print_ascii()
        except ImportError:
            print(
                "(ASCII omitido) Instale: pip install grandalf\n"
                "  ou instale dependências de desenvolvimento: pip install -r requirements-dev.txt",
                file=sys.stderr,
            )

    if not args.no_png:
        png_path = _REPO_ROOT / "salespilot_graph.png"
        try:
            png_bytes = gx.draw_mermaid_png(max_retries=3, retry_delay=2.0)
            png_path.write_bytes(png_bytes)
            print(f"\nOK: {png_path}", flush=True)
        except Exception as e:  # noqa: BLE001 — queremos qualquer falha de rede/API
            print(
                f"\n(PNG omitido) {e}\n"
                "  Abra salespilot_graph.mmd no VS Code ou em https://mermaid.live e exporte como PNG.",
                file=sys.stderr,
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
