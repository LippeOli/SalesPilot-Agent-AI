"""
SalesPilot — Grafo ReAct (LangGraph)

Topologia do grafo (padrão ReAct clássico):

    START
      │
      ▼
   [agent]  ──── tools_condition ────► [tools]
      ▲                                   │
      └───────────────────────────────────┘
      │
      ▼  (quando tools_condition retorna END — resposta final)
     END

Ciclo Reasoning/Acting:
  • Reasoning: o nó 'agent' envia as mensagens ao LLM (com ferramentas vinculadas).
    O modelo decide se precisa de dados externos → emite tool_calls.
  • Acting:    o nó 'tools' executa a ferramenta e devolve um ToolMessage.
    O agente recebe o resultado e pode encadear mais chamadas ou finalizar.
"""

import os

from langchain_core.messages import SystemMessage
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from salespilot.tools import TOOLS

# ---------------------------------------------------------------------------
# Persona do agente
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = SystemMessage(content="""
Você é o SalesPilot, um assistente de vendas inteligente e colaborativo.

Seu papel é ser o parceiro estratégico do vendedor, ajudando-o a:
  • Verificar disponibilidade de estoque antes de confirmar pedidos
  • Validar se descontos comerciais estão dentro das políticas da empresa (máximo 15%)
  • Atualizar o status dos leads no funil de vendas em tempo real

⚠️ REGRA OBRIGATÓRIA — siga SEMPRE, sem exceção:
  1. NUNCA confirme a disponibilidade de um produto sem antes chamar consultar_estoque.
  2. NUNCA aprove um desconto sem antes chamar validar_regra_negocio.
  3. Só atualize o status do lead (atualizar_lead) após os dois pontos acima estarem validados.
  Ignorar estas regras compromete as operações da empresa.

Diretrizes de comportamento:
  - Se um desconto exceder 15%, informe claramente que é necessária aprovação do supervisor.
  - Seja proativo: antecipe dúvidas e sugira próximos passos no funil.
  - Responda sempre em português brasileiro.
  - Mantenha um tom profissional, direto e encorajador.

Ferramentas disponíveis:
  - consultar_estoque: verifica unidades disponíveis de um produto
  - validar_regra_negocio: aprova ou rejeita o desconto solicitado
  - atualizar_lead: registra o novo status do cliente no funil
""")


# ---------------------------------------------------------------------------
# LLM factory — troca entre Ollama e OpenAI via variável de ambiente
# ---------------------------------------------------------------------------

def build_llm():
    """
    Retorna uma instância do modelo de chat com base em MODEL_PROVIDER.

    Para usar Ollama (padrão — sem API key):
        MODEL_PROVIDER=ollama  (ou omitir a variável)
        Ollama deve estar rodando: `ollama serve`

    Para usar OpenAI:
        MODEL_PROVIDER=openai
        OPENAI_API_KEY=sk-...
    """
    provider = os.getenv("MODEL_PROVIDER", "ollama").lower()

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0,
        )

    from langchain_ollama import ChatOllama
    return ChatOllama(
        model=os.getenv("OLLAMA_MODEL", "llama3.2"),
        temperature=0,
    )


# ---------------------------------------------------------------------------
# Construção do grafo
# ---------------------------------------------------------------------------

def build_graph():
    """Compila e retorna o app LangGraph do SalesPilot."""
    llm = build_llm()
    llm_with_tools = llm.bind_tools(TOOLS)

    def agent_node(state: MessagesState):
        messages = [SYSTEM_PROMPT] + state["messages"]
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    graph = StateGraph(MessagesState)

    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(TOOLS))

    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")

    return graph.compile()


app = build_graph()
