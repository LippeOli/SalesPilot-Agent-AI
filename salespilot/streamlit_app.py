"""
Interface Streamlit do SalesPilot com upload de PDFs e RAG.

Execute:
    streamlit run salespilot/streamlit_app.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import httpx
import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage

load_dotenv()

# Garante imports absolutos `salespilot.*` quando o Streamlit coloca só `salespilot/` no sys.path.
_REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from salespilot.agent import build_graph
from salespilot.rag import MAX_PDF_FILES, build_vectorstore_from_pdfs
from salespilot.tools import BASE_TOOLS, make_buscar_documentos


def _ollama_down_message() -> str:
    return (
        "Ollama não está acessível (connection refused na porta típica 11434). "
        "Em outro terminal rode: ollama serve. "
        "Instale o modelo de chat: ollama pull llama3.2 (ou o valor de OLLAMA_MODEL no .env). "
        "Para indexar PDFs com Ollama: ollama pull nomic-embed-text. "
        "Se o Ollama estiver em outro host/porta, defina OLLAMA_HOST conforme a documentação do Ollama."
    )


def _init_session() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "vectorstore" not in st.session_state:
        st.session_state.vectorstore = None
    if "graph" not in st.session_state:
        st.session_state.graph = build_graph()
    if "indexed_names" not in st.session_state:
        st.session_state.indexed_names = []


def _reset_chat() -> None:
    st.session_state.messages = []


def main() -> None:
    st.set_page_config(page_title="SalesPilot", layout="wide")
    _init_session()

    st.title("SalesPilot")
    st.caption("Assistente de vendas com LangGraph, ferramentas de CRM e RAG sobre PDFs.")

    with st.sidebar:
        st.subheader("Usuário")
        st.text_input("Nome ou ID", key="user_id", placeholder="ex.: Ana — equipe Sul")

        st.subheader("Documentos (RAG)")
        uploaded = st.file_uploader(
            f"PDFs (máx. {MAX_PDF_FILES})",
            type=["pdf"],
            accept_multiple_files=True,
        )
        if uploaded and len(uploaded) > MAX_PDF_FILES:
            st.warning(f"Somente os primeiros {MAX_PDF_FILES} arquivos serão usados.")

        if st.button("Indexar documentos", type="primary"):
            if not uploaded:
                st.error("Selecione pelo menos um PDF antes de indexar.")
            else:
                files = list(uploaded)[:MAX_PDF_FILES]
                tmp_paths: list[str] = []
                try:
                    for f in files:
                        suffix = Path(f.name).suffix or ".pdf"
                        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                        tmp.write(f.getbuffer())
                        tmp.close()
                        tmp_paths.append(tmp.name)

                    with st.spinner("Indexando PDFs (embeddings + FAISS)…"):
                        vs = build_vectorstore_from_pdfs(tmp_paths)
                    st.session_state.vectorstore = vs
                    st.session_state.indexed_names = [f.name for f in files]
                    st.session_state.graph = build_graph(
                        tools=BASE_TOOLS + [make_buscar_documentos(vs)],
                    )
                    st.success(f"Indexados: {', '.join(st.session_state.indexed_names)}")
                except httpx.ConnectError:
                    st.session_state.vectorstore = None
                    st.session_state.indexed_names = []
                    st.session_state.graph = build_graph()
                    st.error(_ollama_down_message())
                except Exception as e:
                    st.error(f"Falha ao indexar: {e}")
                    st.session_state.vectorstore = None
                    st.session_state.indexed_names = []
                    st.session_state.graph = build_graph()
                finally:
                    for p in tmp_paths:
                        Path(p).unlink(missing_ok=True)

        if st.session_state.indexed_names:
            st.info("Arquivos no índice:\n- " + "\n- ".join(st.session_state.indexed_names))
        else:
            st.caption("Nenhum PDF indexado — o agente ainda pode usar estoque, desconto e leads.")

        if st.button("Limpar conversa"):
            _reset_chat()
            st.rerun()

    prompt = st.chat_input("Envie uma mensagem…")

    if prompt:
        uid = (st.session_state.get("user_id") or "").strip()
        text = f"[{uid}] {prompt}" if uid else prompt
        st.session_state.messages.append(HumanMessage(content=text))

    for msg in st.session_state.messages:
        role = "user" if isinstance(msg, HumanMessage) else "assistant"
        with st.chat_message(role):
            st.markdown(msg.content)

    if prompt:
        final_response = ""
        with st.chat_message("assistant"):
            status = st.status("SalesPilot processando…", expanded=False)
            try:
                for chunk in st.session_state.graph.stream(
                    {"messages": st.session_state.messages},
                ):
                    for node_name, data in chunk.items():
                        msgs = data.get("messages", [])
                        for m in msgs:
                            if getattr(m, "content", ""):
                                final_response = str(m.content)
                            tcs = getattr(m, "tool_calls", None) or []
                            for tc in tcs:
                                status.write(f"{node_name}: `{tc.get('name', '?')}`")
            except httpx.ConnectError:
                if (
                    st.session_state.messages
                    and isinstance(st.session_state.messages[-1], HumanMessage)
                ):
                    st.session_state.messages.pop()
                status.update(label="Erro de conexão", state="error")
                st.error(_ollama_down_message())
                st.stop()
            else:
                status.update(label="Concluído", state="complete")

            if final_response:
                st.markdown(final_response)
                st.session_state.messages.append(AIMessage(content=final_response))
            else:
                st.warning("Nenhuma resposta textual foi gerada. Tente reformular a pergunta.")


if __name__ == "__main__":
    main()
