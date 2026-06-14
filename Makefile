# SalesPilot — tarefas comuns (macOS / Linux; requer GNU Make)
PYTHON ?= python3
VENV   ?= .venv
PY     := $(VENV)/bin/python
PIP    := $(VENV)/bin/pip

.DEFAULT_GOAL := help

.PHONY: help venv install setup env-copy run run-rag streamlit clean distclean

help: ## Mostra esta ajuda
	@grep -hE '^[a-zA-Z0-9_-]+:.*?##' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

venv: ## Cria o ambiente virtual em .venv
	@test -d "$(VENV)" || $(PYTHON) -m venv "$(VENV)"
	@echo "Virtualenv pronto: $(VENV)"

install: venv ## Instala dependências (pip install -r requirements.txt)
	"$(PIP)" install --upgrade pip
	"$(PIP)" install -r requirements.txt

setup: install ## Alias: venv + dependências (primeiro uso típico)
	@echo "Execute: cp .env.example .env  (se ainda não existir .env)"

env-copy: ## Copia .env.example para .env (não sobrescreve .env existente)
	@test -f .env && echo ".env já existe; não alterado." || (cp .env.example .env && echo "Criado .env a partir de .env.example")

run: ## Inicia a CLI sem RAG (python -m salespilot.main)
	@test -x "$(PY)" || (echo "Execute: make setup"; exit 1)
	"$(PY)" -m salespilot.main

run-rag: ## CLI com RAG; defina PDFS="a.pdf b.pdf" (até 5 arquivos)
	@test -x "$(PY)" || (echo "Execute: make setup"; exit 1)
	@if [ -z "$(PDFS)" ]; then \
		echo 'Uso: make run-rag PDFS="docs/manual.pdf"'; \
		echo '     make run-rag PDFS="a.pdf b.pdf"'; \
		exit 1; \
	fi
	"$(PY)" -m salespilot.main --pdfs $(PDFS)

streamlit: ## Interface web (streamlit run salespilot/streamlit_app.py)
	@test -x "$(VENV)/bin/streamlit" || (echo "Execute: make setup"; exit 1)
	"$(VENV)/bin/streamlit" run salespilot/streamlit_app.py

clean: ## Remove caches Python (__pycache__, .pyc)
	@find . -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name '*.py[co]' -delete 2>/dev/null || true

distclean: clean ## Remove também a pasta .venv
	@rm -rf "$(VENV)"
	@echo "Removido .venv"
