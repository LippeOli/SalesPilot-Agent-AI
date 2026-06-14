"""
RAG — ingestão de PDFs, chunking, embeddings e índice FAISS em memória.

Usa o mesmo MODEL_PROVIDER que o chat (ollama | openai). Para embeddings Ollama,
defina OLLAMA_EMBED_MODEL (ex.: nomic-embed-text) e tenha o modelo puxado no Ollama.
"""

from __future__ import annotations

import os
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

MAX_PDF_FILES = 5
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
DEFAULT_TOP_K = 4


def build_embeddings():
    """
    Retorna embeddings conforme MODEL_PROVIDER (mesma lógica conceitual do chat).

    OpenAI: OPENAI_EMBED_MODEL (padrão text-embedding-3-small).
    Ollama: OLLAMA_EMBED_MODEL (padrão nomic-embed-text).
    """
    provider = os.getenv("MODEL_PROVIDER", "ollama").lower()

    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(
            model=os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small"),
        )

    from langchain_ollama import OllamaEmbeddings

    return OllamaEmbeddings(
        model=os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text"),
    )


def load_documents_from_pdfs(paths: list[str]) -> list[Document]:
    """
    Carrega e concatena documentos de até MAX_PDF_FILES caminhos de PDF.

    Raises:
        ValueError: se a lista estiver vazia ou exceder o limite.
    """
    if not paths:
        raise ValueError("Informe pelo menos um caminho de PDF.")
    if len(paths) > MAX_PDF_FILES:
        raise ValueError(f"No máximo {MAX_PDF_FILES} arquivos PDF são permitidos.")

    all_docs: list[Document] = []
    for p in paths:
        path = Path(p)
        if not path.is_file():
            raise ValueError(f"Arquivo não encontrado: {p}")
        if path.suffix.lower() != ".pdf":
            raise ValueError(f"Esperado arquivo .pdf: {p}")
        loader = PyPDFLoader(str(path))
        all_docs.extend(loader.load())
    return all_docs


def _split_documents(documents: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    return splitter.split_documents(documents)


def format_chunks_for_llm(documents: list[Document]) -> str:
    """Formata trechos recuperados com nome do arquivo e conteúdo."""
    if not documents:
        return "Nenhum trecho relevante foi encontrado nos documentos indexados."

    parts: list[str] = []
    for i, doc in enumerate(documents, start=1):
        source = doc.metadata.get("source") or "fonte_desconhecida"
        name = Path(str(source)).name
        page = doc.metadata.get("page")
        loc = f" (página {page + 1})" if isinstance(page, int) else ""
        parts.append(f"[{i}] Arquivo: {name}{loc}\n{doc.page_content.strip()}")
    return "\n\n---\n\n".join(parts)


def similarity_search_formatted(vectorstore: FAISS, query: str, k: int = DEFAULT_TOP_K) -> str:
    """Executa busca por similaridade e devolve string pronta para o LLM."""
    docs = vectorstore.similarity_search(query, k=k)
    return format_chunks_for_llm(docs)


def build_vectorstore_from_pdfs(paths: list[str]) -> FAISS:
    """
    Carrega PDFs, divide em chunks, gera embeddings e constrói FAISS em memória.

    Returns:
        Instância FAISS pronta para similarity_search.
    """
    raw_docs = load_documents_from_pdfs(paths)
    if not raw_docs:
        raise ValueError("Nenhum texto foi extraído dos PDFs (PDFs vazios ou só imagem?).")

    chunks = _split_documents(raw_docs)
    embeddings = build_embeddings()
    return FAISS.from_documents(chunks, embeddings)
