# SalesPilot — Orquestrador de Funil de Vendas (CRM Inteligente)

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-ReAct-green)
![LLM](https://img.shields.io/badge/LLM-Ollama%20%7C%20OpenAI-orange)

Agente de IA colaborativo que auxilia equipes de vendas a gerenciar leads, validar condições comerciais em tempo real e automatizar o registro de etapas do funil de vendas — via **terminal** ou **Streamlit**. Com PDFs indexados, o mesmo grafo ReAct ganha a ferramenta **`buscar_documentos`**, que recupera trechos relevantes em um índice **FAISS** em memória (RAG).

---

## O que é o SalesPilot?

O SalesPilot é um **agente ReAct** (Reasoning + Acting) construído com [LangGraph](https://langchain-ai.github.io/langgraph/) que age como um parceiro estratégico do vendedor. Antes de aprovar qualquer operação comercial, ele:

- Consulta o estoque para garantir que o produto está disponível
- Valida se o desconto solicitado respeita a política da empresa (máximo 15%)
- Atualiza o status do lead no funil de vendas somente após as validações acima

O agente mantém o histórico da conversa durante toda a sessão, permitindo um diálogo contínuo e contextualizado.

### RAG em PDF (até 5 arquivos)

- Os PDFs são lidos com **PyPDFLoader**, divididos com **RecursiveCharacterTextSplitter** (chunks ~800 caracteres, sobreposição 100) e indexados com **embeddings** + **FAISS** (`salespilot/rag.py`).
- O modelo de chat continua sendo o de `MODEL_PROVIDER`; os embeddings seguem o mesmo provedor (`OpenAIEmbeddings` ou `OllamaEmbeddings`). Para **Ollama**, instale um modelo de embedding, por exemplo: `ollama pull nomic-embed-text`, e configure `OLLAMA_EMBED_MODEL` se quiser outro nome.
- **OpenAI:** embeddings usam a mesma `OPENAI_API_KEY` que o chat; há custo por token. Opcional: `OPENAI_EMBED_MODEL` (padrão `text-embedding-3-small`).
- PDFs escaneados só como imagem **não** têm texto extraível — use PDFs com texto selecionável na demonstração.

#### PDFs de demonstração (repositório)

Na pasta [`docs/demo_rag/`](docs/demo_rag/) há cinco PDFs gerados para testar o RAG (política de desconto, catálogo com quantidades alinhadas ao `tools.py`, funil, FAQ e manual do notebook com **garantia de 36 meses**).

Para **regenerar** os arquivos (ex.: após editar o script):

```bash
pip install -r requirements-dev.txt   # inclui fpdf2
python scripts/generate_demo_pdfs.py
```

**Teste rápido na CLI** (com Ollama no ar e `nomic-embed-text` se usar embeddings locais):

```bash
make run-rag PDFS="docs/demo_rag/politica_descontos.pdf docs/demo_rag/catalogo_estoque.pdf docs/demo_rag/funil_vendas.pdf docs/demo_rag/faq_vendas.pdf docs/demo_rag/manual_notebook_empresa_x.pdf"
```

Exemplos de pergunta: *Qual a garantia do Notebook Empresa X no manual?* · *Quantas unidades de notebook constam no catálogo interno?* · *Qual o teto de desconto sem supervisor na política?*

No **Streamlit**, faça upload dos cinco arquivos de `docs/demo_rag/`, clique em **Indexar documentos** e use as mesmas perguntas.

---

## Como funciona — Ciclo ReAct

O grafo implementa o padrão clássico **Reasoning → Acting**:

```mermaid
---
config:
  flowchart:
    curve: linear
---
graph TD;
	__start__([<p>__start__</p>]):::first
	agent(agent)
	tools(tools)
	__end__([<p>__end__</p>]):::last
	__start__ --> agent;
	agent -.-> __end__;
	agent -.-> tools;
	tools --> agent;
	classDef default fill:#f2f0ff,line-height:1.2
	classDef first fill-opacity:0
	classDef last fill:#bfb6fc
```

| Fase | Nó | O que acontece |
|---|---|---|
| **Reasoning** | `agent` | O LLM recebe o histórico + system prompt, raciocina e decide quais ferramentas chamar. Emite `tool_calls` se precisar de dados. |
| **Acting** | `tools` | `ToolNode` executa a ferramenta solicitada e devolve o resultado como `ToolMessage`. O ciclo recomeça até a resposta final. Quando há índice RAG, este nó também executa `buscar_documentos`. |

**Exemplo de fluxo** para *"Fechar notebook com 10% de desconto para Ana Souza"*:
1. `[RACIOCÍNIO]` → chama `consultar_estoque("notebook")` → 10 unidades disponíveis
2. `[RACIOCÍNIO]` → chama `validar_regra_negocio(valor, 10.0)` → APROVADO
3. `[RACIOCÍNIO]` → chama `atualizar_lead("Ana Souza", "Fechado")` → atualizado
4. `[RACIOCÍNIO]` → resposta final ao vendedor → `END`

---

## Estrutura do projeto

```
SalesPilot-Agent-AI/
├── Makefile                  # Atalhos: setup, run, streamlit, run-rag
├── requirements.txt          # Dependências Python (runtime do agente)
├── requirements-dev.txt      # fpdf2 — só para scripts/generate_demo_pdfs.py
├── .env.example              # Template de configuração do ambiente
├── .gitignore
├── scripts/
│   └── generate_demo_pdfs.py # Gera os PDFs em docs/demo_rag/
├── docs/
│   └── demo_rag/             # PDFs de exemplo para RAG
└── salespilot/
    ├── __init__.py           # Re-exporta `app` para uso externo
    ├── rag.py                # PDFs, chunks, embeddings, FAISS
    ├── tools.py              # Ferramentas @tool (CRM + factory RAG)
    ├── agent.py              # LLM factory, system prompt, build_graph()
    ├── main.py               # CLI (app.stream); opcional --pdfs para RAG
    └── streamlit_app.py      # UI: upload PDF, indexar, chat
```

---

## Ferramentas do agente

| Ferramenta | Parâmetros | Comportamento |
|---|---|---|
| `consultar_estoque` | `produto: str` | Retorna a quantidade em estoque. Indica "SEM ESTOQUE" se zerado. |
| `validar_regra_negocio` | `valor_venda: float`, `desconto_percentual: float` | Aprova automaticamente descontos ≤ 15%. Acima disso, exige aprovação do supervisor. |
| `atualizar_lead` | `nome_cliente: str`, `novo_status: str` | Registra a mudança de estágio no funil. Auto-cria o lead se não existir. |
| `buscar_documentos` | `query: str` | *(Somente com PDFs indexados.)* Recupera trechos dos manuais/políticas carregados via FAISS. |

**Estágios do funil:** `Prospecção → Qualificação → Proposta → Negociação → Fechado → Perdido`

---

## Instalação

**Pré-requisitos:** Python 3.11+ e [Ollama](https://ollama.com) instalado localmente (ou uma chave de API da OpenAI).

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/SalesPilot-Agent-AI.git
cd SalesPilot-Agent-AI

# 2. Crie e ative um ambiente virtual
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Instale as dependências
pip install -r requirements.txt

# (Opcional) Para regenerar os PDFs demo em docs/demo_rag/
# pip install -r requirements-dev.txt && python scripts/generate_demo_pdfs.py

# 4. Configure o ambiente
cp .env.example .env
# Edite o .env se quiser usar OpenAI (veja seção "Troca de modelo")
```

### Makefile (atalhos)

Requer **GNU Make** (macOS e a maioria das distros Linux já incluem). Cria/uso o virtualenv em `.venv` e chama os executáveis de dentro dele.

| Comando | O que faz |
|---------|-----------|
| `make help` | Lista os alvos disponíveis (é o padrão ao rodar só `make`). |
| `make setup` | Cria `.venv` (se faltar) e instala `requirements.txt`. |
| `make install` | Garante `.venv` e reinstala dependências. |
| `make env-copy` | Copia `.env.example` → `.env` apenas se `.env` ainda não existir. |
| `make run` | CLI sem RAG (`python -m salespilot.main`). |
| `make run-rag PDFS="arq.pdf"` | CLI com RAG; até 5 PDFs, separados por espaço entre aspas. |
| `make streamlit` | Abre a UI Streamlit. |
| `make clean` | Remove `__pycache__` e `.pyc`. |
| `make distclean` | `clean` + remove a pasta `.venv`. |

**Primeiro uso com Make:**

```bash
make setup
make env-copy
# Edite .env se necessário; suba o Ollama (e modelos de chat + embedding para RAG)
make run
```

**RAG na linha de comando:**

```bash
make run-rag PDFS="docs/politica.pdf docs/faq.pdf"
```

**Interface com upload de PDF:**

```bash
make streamlit
```

No Windows, o `Makefile` pressupõe caminhos estilo Unix (`/bin/sh`, `.venv/Scripts` não é usado aqui). Nesse caso use os comandos `python -m venv` e `pip` manualmente como na seção anterior.

---

## Como executar

### Terminal (sem RAG)

```bash
# Suba o Ollama com o modelo llama3.2 (em outro terminal)
ollama pull llama3.2
ollama serve

# Inicie o SalesPilot
python -m salespilot.main
```

Equivalente com Make (após `make setup`): `make run`.

### Terminal com RAG (PDFs na inicialização)

Até **5** caminhos de arquivo `.pdf`:

```bash
python -m salespilot.main --pdfs docs/politica_descontos.pdf docs/faq_produtos.pdf
```

Com Make: `make run-rag PDFS="docs/politica_descontos.pdf docs/faq_produtos.pdf"`.

### Streamlit (upload e indexação na interface)

```bash
# Recomendado: mesmo provedor de embeddings que o chat (veja .env.example)
ollama pull nomic-embed-text   # se MODEL_PROVIDER=ollama

streamlit run salespilot/streamlit_app.py
```

Com Make: `make streamlit`.

Na barra lateral: envie até cinco PDFs, clique em **Indexar documentos** e converse no chat. O campo **Nome ou ID** prefixa as mensagens (simulação multiusuário leve).

**Saída esperada no terminal:**

```
╔══════════════════════════════════════════════════════╗
║          SalesPilot — Assistente de Vendas IA        ║
║  Digite sua mensagem. 'sair' ou Ctrl+C para encerrar ║
╚══════════════════════════════════════════════════════╝

Vendedor: Quero fechar um notebook com 10% de desconto para Ana Souza

--- SalesPilot processando ---

  [RACIOCÍNIO] Chamando ferramenta: consultar_estoque
               Argumentos: {'produto': 'notebook'}

  [FERRAMENTA] Produto 'notebook': 10 unidades disponíveis.

  [RACIOCÍNIO] Chamando ferramenta: validar_regra_negocio
               Argumentos: {'valor_venda': 3500.0, 'desconto_percentual': 10.0}

  [FERRAMENTA] APROVADO. Desconto de 10.0% dentro do limite (15.0%). Valor final: R$ 3.150,00.

  [RACIOCÍNIO] Chamando ferramenta: atualizar_lead
               Argumentos: {'nome_cliente': 'Ana Souza', 'novo_status': 'Fechado'}

  [FERRAMENTA] Lead 'Ana Souza' atualizado: 'Prospecção' → 'Fechado'.

  [RACIOCÍNIO] Tudo certo! Venda do notebook aprovada com 10% de desconto...

-----------------------------
```

---

## Visualizar o grafo

O script `generate_diagram.py` gera o diagrama do grafo LangGraph em três formatos:

```bash
# Instale a dependência para o diagrama ASCII (uma vez só)
pip install grandalf

# Gere o diagrama
python generate_diagram.py
```

| Saída | Formato | Como visualizar |
|---|---|---|
| Terminal | ASCII | Exibido direto no terminal |
| `salespilot_graph.mmd` | Mermaid | Abra no VS Code com a extensão **Mermaid Preview**, ou cole em [mermaid.live](https://mermaid.live) |
| `salespilot_graph.png` | PNG | Requer internet — gerado automaticamente via mermaid.ink API |

---

## Troca de modelo

A troca entre Ollama e OpenAI não requer nenhuma mudança de código — apenas variáveis de ambiente:

| Provedor | Configuração no `.env` |
|---|---|
| Ollama llama3.2 (padrão) | `MODEL_PROVIDER=ollama` (ou omitir) |
| Outro modelo Ollama | `MODEL_PROVIDER=ollama` + `OLLAMA_MODEL=mistral` |
| OpenAI GPT-4o-mini | `MODEL_PROVIDER=openai` + `OPENAI_API_KEY=sk-...` |
| Outro modelo OpenAI | `MODEL_PROVIDER=openai` + `OPENAI_MODEL=gpt-4o` |
| Embeddings Ollama (RAG) | `OLLAMA_EMBED_MODEL=nomic-embed-text` (ou outro modelo de embedding instalado) |
| Embeddings OpenAI (RAG) | `OPENAI_EMBED_MODEL=text-embedding-3-small` (opcional; padrão já cobre RAG) |

### Problemas comuns

**`httpx.ConnectError` / `[Errno 61] Connection refused` com Ollama**

O processo Python não conseguiu abrir conexão TCP com o servidor do Ollama (em geral `127.0.0.1:11434`). Isso costuma significar que o Ollama **não está rodando**.

1. Em outro terminal: `ollama serve` (ou use o app do Ollama no macOS/Windows).
2. Instale o modelo de chat: `ollama pull llama3.2` (ou o modelo definido em `OLLAMA_MODEL`).
3. Se usar **RAG** com Ollama, instale também um modelo de embedding: `ollama pull nomic-embed-text`.

Se o Ollama estiver em outra máquina ou porta, configure `OLLAMA_HOST` conforme a [documentação do Ollama](https://github.com/ollama/ollama/blob/main/docs/faq.md).

---

## Exemplos de uso

### Cenário 1 — Produto sem estoque (bloqueio)
```
Vendedor: Quero vender um celular para Carlos Lima com 5% de desconto
SalesPilot: Produto 'celular' está SEM ESTOQUE no momento. Não é possível
            prosseguir com esta venda. Deseja verificar outro produto?
```

### Cenário 2 — Desconto acima do limite (requer supervisor)
```
Vendedor: Quero dar 20% de desconto no notebook para Beatriz Melo
SalesPilot: O desconto de 20% excede o limite de 15% permitido para aprovação
            autônoma. Esta venda REQUER APROVAÇÃO DO SUPERVISOR antes de ser
            confirmada.
```

### Cenário 3 — Fluxo completo aprovado
```
Vendedor: Fecha negócio do teclado com 12% de desconto para Rafael Torres
SalesPilot: Tudo verificado e aprovado! Estoque OK (30 un.), desconto de 12%
            dentro do limite. Rafael Torres atualizado para 'Fechado' no funil.
```

---

## Stack técnica

| Tecnologia | Versão | Papel |
|---|---|---|
| [LangGraph](https://langchain-ai.github.io/langgraph/) | ≥ 0.2 | Orquestração do grafo ReAct (StateGraph, ToolNode, tools_condition) |
| [LangChain Core](https://python.langchain.com/) | ≥ 0.3 | Mensagens, ferramentas (@tool), abstrações de LLM |
| [langchain-ollama](https://pypi.org/project/langchain-ollama/) | ≥ 0.2 | Integração com modelos locais via Ollama |
| [langchain-openai](https://pypi.org/project/langchain-openai/) | ≥ 0.2 | Integração com a API da OpenAI |
| [python-dotenv](https://pypi.org/project/python-dotenv/) | ≥ 1.0 | Carregamento de variáveis de ambiente |
| [Streamlit](https://streamlit.io/) | ≥ 1.28 | Interface web, upload de PDFs e chat |
| [FAISS](https://github.com/facebookresearch/faiss) (`faiss-cpu`) | ≥ 1.8 | Busca vetorial em memória para RAG |
| [langchain-community](https://pypi.org/project/langchain-community/) | ≥ 0.3 | PyPDFLoader, vector store FAISS |
| [langchain-text-splitters](https://pypi.org/project/langchain-text-splitters/) | ≥ 0.3 | `RecursiveCharacterTextSplitter` |
| [pypdf](https://pypi.org/project/pypdf/) | ≥ 4.0 | Leitura de PDFs |
| Python | 3.11+ | Linguagem base |

---

## Licença

MIT © 2026 Felipe Oliveira
