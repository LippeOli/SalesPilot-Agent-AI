"""
Ponto de entrada do SalesPilot — interface de terminal interativa.

Como executar:
    python -m salespilot.main
    # ou
    python salespilot/main.py

Com RAG (até 5 PDFs indexados na inicialização):
    python -m salespilot.main --pdfs manual.pdf politica.pdf
"""

from __future__ import annotations

import argparse
import os

import httpx

# load_dotenv() deve ser chamado ANTES de importar o agent,
# pois o agent lê MODEL_PROVIDER e OPENAI_API_KEY na importação.
from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import AIMessage, HumanMessage

BANNER = """
╔══════════════════════════════════════════════════════╗
║          SalesPilot — Assistente de Vendas IA        ║
║  Digite sua mensagem. 'sair' ou Ctrl+C para encerrar ║
╚══════════════════════════════════════════════════════╝
"""

NODE_LABELS = {
    "agent": "RACIOCÍNIO",
    "tools": "FERRAMENTA",
}


def print_step(node_name: str, chunk: dict) -> None:
    """Exibe no terminal um único passo do stream do agente."""
    label = NODE_LABELS.get(node_name, node_name.upper())
    messages = chunk.get(node_name, {}).get("messages", [])
    for msg in messages:
        tool_calls = getattr(msg, "tool_calls", [])
        content = getattr(msg, "content", "")
        if tool_calls:
            for tc in tool_calls:
                print(f"\n  [{label}] Chamando ferramenta: {tc['name']}")
                print(f"           Argumentos: {tc['args']}")
        elif content:
            print(f"\n  [{label}] {content}")


def _print_ollama_connection_help() -> None:
    model = os.getenv("OLLAMA_MODEL", "llama3.2")
    print(
        "\n  [ERRO] Não foi possível conectar ao Ollama (connection refused).\n"
        "         O serviço não está aceitando conexões na URL padrão (porta 11434).\n\n"
        "         O que fazer:\n"
        "           1. Em outro terminal, inicie:  ollama serve\n"
        "           2. Baixe o modelo de chat se ainda não tiver:  ollama pull "
        + model
        + "\n"
        "           3. Com RAG + Ollama, instale também embeddings:  ollama pull nomic-embed-text\n\n"
        "         Se o Ollama estiver em outra máquina/porta, defina OLLAMA_HOST no ambiente\n"
        "         (veja documentação do Ollama).\n"
    )


def main(pdf_paths: list[str] | None = None) -> None:
    if pdf_paths:
        from salespilot.agent import build_graph
        from salespilot.rag import build_vectorstore_from_pdfs
        from salespilot.tools import BASE_TOOLS, make_buscar_documentos

        try:
            vs = build_vectorstore_from_pdfs(pdf_paths)
        except httpx.ConnectError:
            print("Erro ao indexar PDFs: não foi possível conectar ao serviço de embeddings.\n")
            _print_ollama_connection_help()
            raise SystemExit(1)
        except Exception as e:
            print(f"Erro ao indexar PDFs: {e}")
            raise SystemExit(1) from e
        app = build_graph(tools=BASE_TOOLS + [make_buscar_documentos(vs)])
        print(f"\n[RAG] {len(pdf_paths)} PDF(s) indexados. A ferramenta buscar_documentos está ativa.\n")
    else:
        from salespilot.agent import app

    print(BANNER)
    conversation_history: list = []

    while True:
        try:
            user_input = input("\nVendedor: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nSalesPilot encerrado. Boas vendas!")
            break

        if not user_input:
            continue
        if user_input.lower() in {"sair", "exit", "quit"}:
            print("SalesPilot encerrado. Boas vendas!")
            break

        conversation_history.append(HumanMessage(content=user_input))

        print("\n--- SalesPilot processando ---")
        final_response = ""

        try:
            for chunk in app.stream({"messages": conversation_history}):
                for node_name in chunk:
                    print_step(node_name, chunk)
                    agent_msgs = chunk.get("agent", {}).get("messages", [])
                    for msg in agent_msgs:
                        if getattr(msg, "content", ""):
                            final_response = msg.content
        except httpx.ConnectError:
            _print_ollama_connection_help()
            conversation_history.pop()
        except httpx.HTTPStatusError as e:
            print(f"\n  [ERRO] Falha HTTP ao falar com o provedor do modelo: {e}\n")
            conversation_history.pop()

        if final_response:
            conversation_history.append(AIMessage(content=final_response))

        print("\n-----------------------------")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SalesPilot — CLI com opcional RAG em PDFs.")
    parser.add_argument(
        "--pdfs",
        nargs="*",
        default=None,
        metavar="PATH",
        help="Caminhos de até 5 PDFs para indexar na inicialização (FAISS em memória).",
    )
    args = parser.parse_args()
    pdfs = args.pdfs
    if pdfs is not None and len(pdfs) == 0:
        print("Informe ao menos um arquivo: --pdfs arquivo.pdf [...]")
        raise SystemExit(2)
    main(pdf_paths=pdfs)
