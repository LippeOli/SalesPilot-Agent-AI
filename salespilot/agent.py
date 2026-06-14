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

from salespilot.tools import BASE_TOOLS

# ---------------------------------------------------------------------------
# Persona do agente
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT_BASE = """
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
"""

_SYSTEM_PROMPT_RAG = """
Documentos PDF indexados:
  - buscar_documentos: recupera trechos relevantes dos manuais/políticas carregados.
  Quando a pergunta depender do conteúdo desses PDFs, chame buscar_documentos ANTES de concluir.
  Na resposta final, cite explicitamente o nome do arquivo e a ideia dos trechos retornados.
"""


def _has_buscar_documentos(tools: list) -> bool:
    return any(getattr(t, "name", None) == "buscar_documentos" for t in tools)


def build_system_message(tools: list) -> SystemMessage:
    text = _SYSTEM_PROMPT_BASE
    if _has_buscar_documentos(tools):
        text += _SYSTEM_PROMPT_RAG
    return SystemMessage(content=text)


# Mensagem padrão (sem RAG) para compatibilidade com imports antigos
SYSTEM_PROMPT = build_system_message(BASE_TOOLS)


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

def build_graph(tools: list | None = None):
    """
    Compila e retorna o app LangGraph do SalesPilot.

    Args:
        tools: Lista de ferramentas (ex.: BASE_TOOLS + [make_buscar_documentos(vs)]).
               Se None, usa apenas BASE_TOOLS (comportamento CLI legado sem RAG).
    """
    tool_list = BASE_TOOLS if tools is None else tools
    llm = build_llm()
    llm_with_tools = llm.bind_tools(tool_list)
    system_message = build_system_message(tool_list)

    def agent_node(state: MessagesState):
        messages = [system_message] + state["messages"]
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    graph = StateGraph(MessagesState)

    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(tool_list))

    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")

    return graph.compile()


app = build_graph()
