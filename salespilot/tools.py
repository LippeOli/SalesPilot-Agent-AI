from langchain_core.tools import tool

# ---------------------------------------------------------------------------
# Bancos de dados fake — simula chamadas reais a sistemas externos
# ---------------------------------------------------------------------------

_ESTOQUE: dict[str, int] = {
    "notebook":  10,
    "celular":    0,   # sem estoque — demonstra o fluxo de bloqueio
    "monitor":    5,
    "teclado":   30,
    "mouse":     18,
}

_LEADS: dict[str, str] = {
    "ana souza":    "Prospecção",
    "carlos lima":  "Qualificação",
    "beatriz melo": "Proposta",
    "rafael torres": "Negociação",
}

DISCOUNT_LIMIT: float = 15.0  # regra comercial: desconto máximo autônomo (%)


# ---------------------------------------------------------------------------
# Ferramenta 1 — consulta de estoque
# ---------------------------------------------------------------------------

@tool
def consultar_estoque(produto: str) -> str:
    """
    Consulta a quantidade disponível em estoque para um produto.

    Args:
        produto: Nome do produto a ser consultado (não diferencia maiúsculas).

    Returns:
        String informando a quantidade disponível ou que o produto não existe.
    """
    quantidade = _ESTOQUE.get(produto.strip().lower())
    if quantidade is None:
        return f"Produto '{produto}' não encontrado no catálogo."
    if quantidade == 0:
        return f"Produto '{produto}' está SEM ESTOQUE no momento."
    return f"Produto '{produto}': {quantidade} unidades disponíveis."


# ---------------------------------------------------------------------------
# Ferramenta 2 — validação de regra de negócio (desconto)
# ---------------------------------------------------------------------------

@tool
def validar_regra_negocio(valor_venda: float, desconto_percentual: float) -> str:
    """
    Valida se o desconto solicitado está dentro das regras comerciais da empresa.

    Regra: descontos até 15% são aprovados automaticamente.
    Acima disso, é obrigatória a aprovação do supervisor.

    Args:
        valor_venda:          Valor bruto da venda em reais (ex: 5000.0).
        desconto_percentual:  Percentual de desconto solicitado (ex: 10.0 = 10%).

    Returns:
        String com o resultado da validação e o valor final calculado.
    """
    if desconto_percentual < 0:
        return "Desconto inválido: o percentual não pode ser negativo."

    valor_desconto = valor_venda * (desconto_percentual / 100)
    valor_final = valor_venda - valor_desconto

    if desconto_percentual <= DISCOUNT_LIMIT:
        return (
            f"APROVADO. Desconto de {desconto_percentual}% dentro do limite "
            f"({DISCOUNT_LIMIT}%). Valor final: R$ {valor_final:,.2f}."
        )
    return (
        f"REQUER APROVAÇÃO DO SUPERVISOR. Desconto de {desconto_percentual}% "
        f"excede o limite de {DISCOUNT_LIMIT}%. "
        f"Valor final seria: R$ {valor_final:,.2f}."
    )


# ---------------------------------------------------------------------------
# Ferramenta 3 — atualização do lead no funil de vendas
# ---------------------------------------------------------------------------

@tool
def atualizar_lead(nome_cliente: str, novo_status: str) -> str:
    """
    Atualiza o status de um lead no funil de vendas.

    Estágios do funil: Prospecção → Qualificação → Proposta → Negociação → Fechado → Perdido

    Args:
        nome_cliente: Nome do cliente/lead (não diferencia maiúsculas).
        novo_status:  Novo estágio do funil de vendas.

    Returns:
        Confirmação da atualização ou criação automática do lead caso não exista.
    """
    chave = nome_cliente.strip().lower()
    if chave not in _LEADS:
        _LEADS[chave] = novo_status
        return (
            f"Lead '{nome_cliente}' não encontrado. "
            f"Criado automaticamente com status '{novo_status}'."
        )

    status_anterior = _LEADS[chave]
    _LEADS[chave] = novo_status
    return (
        f"Lead '{nome_cliente}' atualizado: '{status_anterior}' → '{novo_status}'."
    )


# Lista exportada para o agent.py
TOOLS = [consultar_estoque, validar_regra_negocio, atualizar_lead]
