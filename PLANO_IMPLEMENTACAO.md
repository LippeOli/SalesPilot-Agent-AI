# Plano de implementação — Sistema colaborativo (LangGraph + RAG + Streamlit)

Este documento descreve **o que implementar** para alinhar o repositório ao enunciado da atividade final: sistema colaborativo com **LangGraph**, **RAG sobre PDFs** (até 5 documentos), **Streamlit**, **múltiplos usuários identificados** e **modelo 3C** (Comunicação, Colaboração, Coordenação).

O código atual (`salespilot/`) já entrega um grafo **ReAct** (agente + `ToolNode`) e interface **CLI**. Use este plano como roteiro incremental: pode-se **estender** o pacote existente ou **criar** um módulo paralelo (ex.: `salespilot/streamlit_app.py`, `salespilot/rag.py`) sem descartar o terminal, se desejarem manter os dois modos de execução.

---

## 1. Objetivo e critérios de aceite

Ao final, o sistema deve permitir:

| Critério | Aceite verificável |
|----------|---------------------|
| LangGraph | Fluxo explícito no código; diagrama no README ou `.mmd` atualizado. |
| RAG em PDF | Usuário carrega ou aponta até **5** PDFs; consultas recuperam trechos relevantes. |
| Ferramenta(s) | Pelo menos **uma** tool claramente útil ao cenário (ex.: `buscar_documentos`). Opcional: sumarização, registro de decisão, votação. |
| Multiusuário | Mensagens com **nome ou ID** visível no histórico e passadas ao grafo (metadata ou prefixo no conteúdo). |
| Streamlit | App executável com `streamlit run ...`; instruções no README. |
| 3C | Seção na documentação ligando **Comunicação**, **Colaboração** e **Coordenação** a telas/fluxos concretos. |

---

## 2. Arquitetura sugerida

```
┌─────────────────────────────────────────────────────────────┐
│                     Streamlit (UI)                          │
│  - seleção / upload PDFs (≤5)                               │
│  - identificação do usuário (nome ou ID)                    │
│  - chat + painel de contexto RAG + decisões / votação       │
└───────────────────────────┬─────────────────────────────────┘
                            │ invoke / stream
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  LangGraph (StateGraph)                     │
│  START → agent (LLM + tools) ⇄ tools (ToolNode) → END      │
│  Estado: mensagens + (opcional) metadados de sessão          │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  RAG: ingestão PDF → chunk → embed → vector store in-memory │
│  Tool: buscar_documentos(query) → top-k trechos             │
└─────────────────────────────────────────────────────────────┘
```

**Decisão de desenho:** manter o padrão **ReAct** atual é válido; basta **adicionar** a tool de recuperação e o pipeline RAG carregado na sessão Streamlit. Se quiserem nota alta em “modelagem”, podem **explicitar** nós (ex.: `retrieve` antes do `agent`) — não é obrigatório se o fluxo estiver bem explicado no diagrama.

---

## 3. Dependências a adicionar

Incluir em `requirements.txt` (versões mínimas indicativas; ajustem após teste local):

```text
streamlit>=1.28.0
pypdf>=4.0.0
langchain-text-splitters>=0.3.0
langchain-community>=0.3.0
```

**Embeddings / vector store (escolher um caminho):**

- **Opção A — rápida e local:** `langchain-community` + `FAISS` (CPU) + embeddings via Ollama (`langchain-ollama` com `OllamaEmbeddings`) ou OpenAI (`langchain-openai` com `OpenAIEmbeddings`).
- **Opção B — simples sem FAISS:** vector store em memória com lista de vetores + similaridade coseno manual (menos dependência, mais código próprio).

**Recomendação:** Opção A com FAISS + mesmos provedores já usados no `build_llm()` reduz atrito com o `.env` existente.

---

## 4. Módulos e arquivos sugeridos

| Arquivo | Responsabilidade |
|---------|------------------|
| `salespilot/rag.py` | Carregar PDFs, dividir em chunks, construir índice, função `build_retriever(pdf_paths)` ou classe `DocumentIndex`. |
| `salespilot/tools.py` | Acrescentar `@tool buscar_documentos(query: str) -> str` que chama o retriever da sessão (ver §5 sobre injeção de contexto). |
| `salespilot/agent.py` | Atualizar `SYSTEM_PROMPT` para o cenário colaborativo + RAG; `build_graph(tools=...)` ou factory que recebe tools dinâmicas. |
| `salespilot/streamlit_app.py` | UI: upload, sidebar usuário, chat, `st.session_state` para histórico e índice RAG. |
| `README.md` | Seção 3C, como rodar Streamlit, como carregar PDFs, diagrama atualizado. |

Opcional: `scripts/generate_diagram.py` — o README já menciona; implementar ou remover a referência.

---

## 5. RAG — fluxo técnico mínimo

1. **Entrada:** lista de caminhos (máx. 5). Validar contagem no Streamlit.
2. **Leitura:** `PyPDFLoader` ou `pypdf` página a página.
3. **Chunking:** `RecursiveCharacterTextSplitter` (ex.: `chunk_size=800`, `chunk_overlap=100`).
4. **Embeddings + store:** indexar todos os chunks; guardar referência em `st.session_state["vectorstore"]`.
5. **Recuperação:** na tool, `similarity_search(query, k=4)` (ou `k=3`) e formatar trechos com **nome do arquivo + trecho** para o LLM citar a fonte.

**Injeção da tool com estado:** em LangGraph, `ToolNode` usa ferramentas sem estado global. Padrões comuns:

- **Closure:** ao montar o grafo na sessão, definir `buscar_documentos` com `nonlocal` / closure sobre o vector store atual; ou
- **Runnable binding:** tool implementada como callable que lê `st.session_state` (acoplamento à UI — simples para trabalho acadêmico); ou
- **Tool com args extras** não expostos ao LLM (menos comum com `@tool` puro).

Para TCC/trabalho, **closure na criação do grafo** após upload dos PDFs costuma ser suficiente e clara.

---

## 6. LangGraph — ajustes no grafo

Manter:

- `StateGraph(MessagesState)` (ou estado customizado se precisarem de `user_id` por mensagem — ver §7).
- Nós `agent` + `tools`, arestas `tools_condition` e loop `tools → agent`.

Alterar:

- `TOOLS` inclui `buscar_documentos` (+ opcionais).
- System prompt: instruir o modelo a **sempre** usar a busca quando a pergunta depender dos PDFs; citar trechos retornados.

**Diagrama:** atualizar `salespilot_graph.mmd` / Mermaid no README se novos nós forem adicionados; se permanecer ReAct, deixe explícito no texto que o **loop** é agente ↔ ferramentas (incluindo RAG).

---

## 7. Multiusuário (simulado)

Requisito mínimo: **identificar** quem falou.

Implementação sugerida:

- No Streamlit: `st.text_input("Nome ou ID do usuário", key="user_id")`.
- Ao enviar mensagem: `HumanMessage(content=f"[{user_id}] {texto}")` **ou** uso de `additional_kwargs={"user_id": ...}` se forem padronizar parsing depois.
- Exibir no chat: `st.chat_message` com `name=user_id` ou avatar por hash do nome.

Não é necessário servidor multi-cliente real; **várias pessoas no mesmo browser** alternando o campo de usuário já “simula” o grupo, desde que o histórico mostre claramente a origem.

---

## 8. Modelo 3C na aplicação e na documentação

| Conceito | Como demonstrar no sistema | Onde documentar |
|----------|----------------------------|-----------------|
| **Comunicação** | Chat com histórico por usuário; mensagens do agente. | README: “canal de mensagens entre membros e agente”. |
| **Colaboração** | Ex.: área “Rascunho da decisão” editável por todos + botão “Pedir síntese ao agente”; ou proposta de texto que o agente consolida com base nos PDFs. | README: fluxo conjunto de construção de resposta. |
| **Coordenação** | Ex.: etapas em `st.expander` ou `st.tabs`: (1) Upload docs (2) Discussão (3) Busca RAG (4) Decisão final; ou tool `registrar_decisao(texto)` que grava em `st.session_state["decisoes"]`. | README: como o fluxo organiza tarefas. |

Pelos menos **um** mecanismo de colaboração/coordenação além do chat puro evita a crítica de “só é um chatbot”.

---

## 9. Ferramentas além da busca (opcional, reforça o enunciado)

Escolham 1–2 para manter o escopo controlado:

| Tool | Função |
|------|--------|
| `buscar_documentos` | **Obrigatória** para o eixo RAG. |
| `sumarizar_trechos` | Recebe texto (ou usa últimos trechos RAG) e devolve resumo. |
| `registrar_decisao` | Append em lista no estado da sessão / arquivo local simples. |
| `votar` | Parâmetros: `opcao: str`; incrementa contador em `st.session_state` — o agente lê totais na próxima rodada. |

---

## 10. Streamlit — esqueleto de telas

1. **Sidebar:** upload PDF (máx. 5), botão “Indexar documentos”, status do índice, campo nome/ID usuário.
2. **Principal:** `st.chat_input` + lista de mensagens; opcional: `st.columns` com chat e “trechos recuperados” da última busca.
3. **Sessão:** `messages`, `vectorstore`, `indexed_files`, `decisoes` (se houver).

**Execução:**

```bash
streamlit run salespilot/streamlit_app.py
```

Documentar no README junto com `python -m salespilot.main` (CLI legado).

---

## 11. Variáveis de ambiente

Reutilizar `MODEL_PROVIDER`, `OLLAMA_MODEL`, `OPENAI_*`. Se usarem embeddings OpenAI, documentar que a **mesma** chave serve e que há custo por embedding.

---

## 12. Testes manuais (checklist antes da entrega)

- [ ] Subir app Streamlit sem erros com 0 PDFs (mensagem clara) e com 1–5 PDFs.
- [ ] Pergunta cujo conteúdo **só** existe no PDF → agente chama `buscar_documentos` e resposta cita trecho.
- [ ] Duas “personas” alternadas no campo usuário → histórico mostra quem falou.
- [ ] Diagrama do grafo reflete o código atual.
- [ ] README: cenário colaborativo, 3C, instalação, `streamlit run`, limites de PDF.
- [ ] Repositório público e URL real no clone (substituir placeholder `seu-usuario`).

---

## 13. Ordem de implementação recomendada

1. `rag.py` + teste unitário manual (script ou notebook) com um PDF de exemplo.
2. Tool `buscar_documentos` + wire no `agent.py` / `TOOLS`.
3. `streamlit_app.py` com upload, indexação e chat usando `app.stream` ou `app.invoke`.
4. Identificação de usuário nas mensagens.
5. Um fluxo extra de **colaboração/coordenação** (tabs, decisão ou votação).
6. README + diagrama + correção da referência ao `generate_diagram.py` (criar ou remover).

---

## 14. Riscos e mitigação

| Risco | Mitigação |
|-------|-----------|
| Ollama sem modelo de embeddings | Usar OpenAI só para embeddings ou modelo Ollama de embedding documentado no README. |
| PDFs escaneados (imagem) | OCR foge do escopo mínimo; usar PDFs com texto selecionável na demo. |
| Latência na indexação | Feedback `st.spinner` e indexação só ao clicar “Indexar”. |

---

## 15. Referências úteis

- [LangGraph — conceitos](https://langchain-ai.github.io/langgraph/)
- [LangChain — RAG overview](https://python.langchain.com/docs/tutorials/rag/)
- [Streamlit — chat elements](https://docs.streamlit.io/develop/api-reference/chat)

---

*Documento gerado para orientar a implementação alinhada ao enunciado da disciplina. Ajustem nomes de módulos e o cenário narrativo (ex.: equipe de vendas + manuais em PDF) conforme a escolha do grupo.*
