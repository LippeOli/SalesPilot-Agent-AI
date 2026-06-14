#!/usr/bin/env python3
"""
Gera cinco PDFs de texto em docs/demo_rag/ para testar o RAG do SalesPilot.

Requisito: pip install -r requirements-dev.txt  (fpdf2)

Uso:
    python scripts/generate_demo_pdfs.py
"""

from __future__ import annotations

from pathlib import Path

from fpdf import FPDF

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "docs" / "demo_rag"


def _write_pdf(filename: str, title: str, paragraphs: list[str]) -> Path:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", size=16)
    pdf.multi_cell(0, 9, title)
    pdf.ln(3)
    pdf.set_font("Helvetica", size=11)
    for block in paragraphs:
        pdf.multi_cell(0, 6, block)
        pdf.ln(3)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / filename
    pdf.output(str(path))
    return path


def main() -> None:
    specs = [
        (
            "politica_descontos.pdf",
            "Política comercial de descontos - SalesPilot (interno)",
            [
                "Este documento define as regras de desconto aplicáveis a vendas "
                "registradas no CRM SalesPilot. A equipe comercial deve seguir "
                "estas diretrizes em todas as negociações, independentemente do canal.",
                "Descontos de até 15% (quinze por cento) sobre o valor bruto da venda "
                "podem ser aprovados de forma autônoma pelo vendedor, sem necessidade "
                "de alçada adicional. O sistema deve registrar o percentual aplicado "
                "e o valor final para auditoria.",
                "Qualquer desconto superior a 15% exige aprovação explícita do "
                "supervisor comercial ou da gerência regional. Enquanto pendente, "
                "a operação não deve ser concluída como 'fechada' no funil sem "
                "a evidência de aprovação.",
                "Exemplo numérico: venda de R$ 4.000,00 com 12% de desconto resulta "
                "em R$ 3.520,00 líquidos - permitido sem supervisor. Já 18% sobre "
                "o mesmo valor exige fluxo de aprovação, pois ultrapassa o limite "
                "autônomo de 15%.",
                "Em campanhas promocionais temporárias, a diretoria pode publicar "
                "percentuais diferentes; enquanto não houver comunicado oficial, "
                "prevalece o teto de 15% descrito neste documento.",
            ],
        ),
        (
            "catalogo_estoque.pdf",
            "Catálogo interno - disponibilidade em estoque (referência RAG)",
            [
                "Valores abaixo referem-se às posições disponíveis para venda imediata "
                "no armazém central. O assistente de vendas pode usar este extrato para "
                "responder dúvidas sobre disponibilidade quando o catálogo for "
                "consultado via documentos.",
                "Notebook: 10 (dez) unidades disponíveis. Monitor: 5 (cinco) unidades. "
                "Teclado: 30 (trinta) unidades. Mouse: 18 (dezoito) unidades.",
                "Celular: 0 (zero) unidades - item sem estoque no momento da última "
                "atualização deste boletim. Não prometer entrega imediata de celular "
                "com base em estoque local sem nova conferência.",
                "Para pedidos acima das quantidades listadas, abrir solicitação de "
                "compra ou transferência entre filiais. Atualize o cliente sobre prazo "
                "realista quando a posição estiver zerada ou crítica.",
                "Produtos fora desta lista devem ser consultados no ERP; este PDF "
                "cobre apenas os itens-piloto usados nas demonstrações do SalesPilot.",
            ],
        ),
        (
            "funil_vendas.pdf",
            "Funil de vendas - estágios e boas práticas (SalesPilot)",
            [
                "O funil padrão do SalesPilot segue a ordem: Prospecção, depois "
                "Qualificação, em seguida Proposta, Negociação, Fechado ou Perdido. "
                "Não pule etapas sem justificativa registrada em notas do lead.",
                "Prospecção: identificação inicial de interesse. Qualificação: "
                "encaixe de necessidade e orçamento. Proposta: envio formal de "
                "condições comerciais. Negociação: ajustes finos de preço e prazo.",
                "Fechado: negócio ganho com documentação mínima concluída. Perdido: "
                "oportunidade encerrada sem venda - registrar motivo para aprendizado.",
                "Atualize o status do lead somente após validar estoque e política "
                "de desconto quando a mudança implicar compromisso de entrega ou "
                "preço fechado. Isso mantém o histórico coerente com as regras do CRM.",
                "Relatórios de conversão usam estas etapas; nomes alternativos não são "
                "aceitos pelo motor de relatórios legado até segunda ordem.",
            ],
        ),
        (
            "faq_vendas.pdf",
            "FAQ - dúvidas frequentes da equipe comercial",
            [
                "P: Qual o desconto máximo sem supervisor? "
                "R: Até 15% autônomo; acima disso exige aprovação do supervisor.",
                "P: Onde vejo quantidades em estoque? "
                "R: Use a ferramenta de estoque do assistente ou o catálogo interno em PDF.",
                "P: Posso marcar 'Fechado' sem checar estoque? "
                "R: Não - confirme disponibilidade antes de prometer entrega.",
                "P: O que fazer se o cliente pedir 20% de desconto? "
                "R: Explique o limite de 15% e acione o supervisor para análise.",
                "P: Celular está disponível? "
                "R: Segundo o catálogo interno, celular está com zero unidades; "
                "não assuma estoque sem nova consulta.",
                "P: Em que ordem avanço o funil? "
                "R: Prospecção -> Qualificação -> Proposta -> Negociação -> Fechado/Perdido.",
                "P: Há garantia específica no notebook Empresa X? "
                "R: Consulte o manual do produto em PDF; lá constam garantia e termos.",
            ],
        ),
        (
            "manual_notebook_empresa_x.pdf",
            "Manual do produto - Notebook Empresa X (série demonstração)",
            [
                "Identificação: Notebook Empresa X, modelo de referência para "
                "demonstrações do SalesPilot. Uso interno e treinamento de equipes.",
                "Especificações resumidas: processador octa-core fictício, 16 GB de RAM, "
                "SSD 512 GB, tela 14 polegadas IPS, peso aproximado 1,35 kg. Conectividade "
                "Wi-Fi 6 e Bluetooth 5.2.",
                "Garantia legal do fabricante: 36 (trinta e seis) meses contra defeitos "
                "de fabricação, contados da data da nota fiscal de venda ao consumidor "
                "final. A garantia não cobre danos por queda, líquidos ou violação do "
                "lacre de manutenção.",
                "Para suporte técnico, abra chamado no portal interno com número de série "
                "e descrição do sintoma. Manutenção fora da rede autorizada invalida a "
                "garantia estendida opcional, quando contratada.",
                "Este manual prevalece sobre folhetos impressos mais antigos que contenham "
                "especificações divergentes. Em caso de dúvida, consulte o time de "
                "especificação de produto antes de responder ao cliente final.",
            ],
        ),
    ]

    for fname, title, paras in specs:
        path = _write_pdf(fname, title, paras)
        print(f"OK {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
