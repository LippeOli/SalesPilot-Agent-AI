"""
Ponto de entrada do SalesPilot — interface de terminal interativa.

Como executar:
    python -m salespilot.main
    # ou
    python salespilot/main.py
"""

# load_dotenv() deve ser chamado ANTES de importar o agent,
# pois o agent lê MODEL_PROVIDER e OPENAI_API_KEY na importação.
from dotenv import load_dotenv
load_dotenv()

from langchain_core.messages import AIMessage, HumanMessage

from salespilot.agent import app

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


def main() -> None:
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

        for chunk in app.stream({"messages": conversation_history}):
            for node_name in chunk:
                print_step(node_name, chunk)
                agent_msgs = chunk.get("agent", {}).get("messages", [])
                for msg in agent_msgs:
                    if getattr(msg, "content", ""):
                        final_response = msg.content

        if final_response:
            conversation_history.append(AIMessage(content=final_response))

        print("\n-----------------------------")


if __name__ == "__main__":
    main()
