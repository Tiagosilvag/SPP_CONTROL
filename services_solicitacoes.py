"""
Regras de negócio de Solicitação de Compra — primeiro passo do fluxo da
obra (Solicitação → Pedido → Baixa). Sempre vinculada a uma obra, e
restrita a materiais Consumível (Patrimoniais previstos na obra são
supridos por Movimentação Patrimonial, não por este fluxo).
"""
from datetime import date
from db import query_all, query_one, execute

STATUS_SOLICITACAO = ["Aberta", "Parcialmente Atendida", "Atendida", "Cancelada"]


def gerar_numero_solicitacao():
    ano = date.today().year
    ultimo = query_one(
        "SELECT numero_solicitacao FROM solicitacoes_compra WHERE numero_solicitacao LIKE ? ORDER BY id DESC LIMIT 1",
        (f"SC-{ano}-%",),
    )
    proximo = 1
    if ultimo:
        try:
            proximo = int(ultimo["numero_solicitacao"].split("-")[-1]) + 1
        except (ValueError, IndexError):
            proximo = 1
    return f"SC-{ano}-{proximo:04d}"


def itens_solicitacao(solicitacao_id):
    return query_all(
        """SELECT si.*, m.nome AS material_nome, m.unidade_medida,
                  (si.quantidade_solicitada - si.quantidade_atendida) AS quantidade_pendente
           FROM solicitacoes_compra_itens si
           JOIN materiais m ON m.id = si.material_id
           WHERE si.solicitacao_id=?
           ORDER BY si.id""",
        (solicitacao_id,),
    )


def solicitacoes_abertas_obra(obra_id):
    """Solicitações da obra com saldo pendente — usadas para popular o
    seletor "qual solicitação atender" ao criar um Pedido de Compra."""
    return query_all(
        """SELECT * FROM solicitacoes_compra
           WHERE obra_id=? AND status IN ('Aberta', 'Parcialmente Atendida')
           ORDER BY data_solicitacao DESC""",
        (obra_id,),
    )


def atualizar_status_solicitacao(solicitacao_id):
    solicitacao = query_one("SELECT status FROM solicitacoes_compra WHERE id=?", (solicitacao_id,))
    if solicitacao is None or solicitacao["status"] == "Cancelada":
        return
    itens = query_all(
        "SELECT quantidade_solicitada, quantidade_atendida FROM solicitacoes_compra_itens WHERE solicitacao_id=?",
        (solicitacao_id,),
    )
    if not itens:
        return
    total_solicitado = sum(i["quantidade_solicitada"] for i in itens)
    total_atendido = sum(i["quantidade_atendida"] for i in itens)
    if total_atendido <= 0:
        novo_status = "Aberta"
    elif total_atendido >= total_solicitado:
        novo_status = "Atendida"
    else:
        novo_status = "Parcialmente Atendida"
    execute("UPDATE solicitacoes_compra SET status=? WHERE id=?", (novo_status, solicitacao_id), audit=False)


def dar_baixa_em_solicitacao(pedido_item, quantidade):
    """Chamada a partir do recebimento de um Pedido de Compra: propaga a
    quantidade recebida para o item de solicitação correspondente, se o
    pedido estiver vinculado a uma Solicitação de Compra."""
    solicitacao_item_id = pedido_item.get("solicitacao_item_id")
    if not solicitacao_item_id:
        return
    execute(
        "UPDATE solicitacoes_compra_itens SET quantidade_atendida = quantidade_atendida + ? WHERE id=?",
        (quantidade, solicitacao_item_id),
    )
    item = query_one("SELECT solicitacao_id FROM solicitacoes_compra_itens WHERE id=?", (solicitacao_item_id,))
    if item:
        atualizar_status_solicitacao(item["solicitacao_id"])
