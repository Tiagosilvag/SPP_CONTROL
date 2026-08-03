"""
Regras de negócio da Obra como entidade central do sistema: cálculo do
painel de materiais (planejado x adquirido x entregue x pendente x
situação).
"""
from db import query_all, query_one, execute

STATUS_OBRA = ["Em Andamento", "Concluída", "Cancelada"]


def _situacao(previsto, entregue):
    if previsto <= 0:
        return "OK" if entregue > 0 else "Pendente"
    if entregue >= previsto:
        return "OK"
    if entregue > 0:
        return "Parcialmente entregue"
    return "Pendente"


def materiais_planejados_obra(obra_id):
    """Lista de materiais planejados da obra com adquirida/entregue/
    pendente/situação calculados — nunca armazenados. Consumíveis são
    supridos via Pedido de Compra + Baixa; Patrimoniais via alocação
    (Movimentação Patrimonial de Transferência entre Obras)."""
    planejados = query_all(
        """SELECT op.*, m.nome AS material_nome, m.unidade_medida, m.tipo_material
           FROM obra_materiais_planejados op
           JOIN materiais m ON m.id = op.material_id
           WHERE op.obra_id=?
           ORDER BY m.tipo_material, m.nome""",
        (obra_id,),
    )

    linhas = []
    for p in planejados:
        linha = dict(p)
        if p["tipo_material"] == "Consumível":
            adquirida = query_one(
                """SELECT COALESCE(SUM(pi.quantidade_solicitada), 0) AS total
                   FROM pedidos_compra_itens pi JOIN pedidos_compra pc ON pc.id = pi.pedido_id
                   WHERE pc.obra_id=? AND pi.material_id=? AND pc.status != 'Cancelado'""",
                (obra_id, p["material_id"]),
            )["total"]
            entregue = query_one(
                """SELECT COALESCE(SUM(ri.quantidade_recebida), 0) AS total
                   FROM recebimento_itens ri
                   JOIN pedidos_compra_itens pi ON pi.id = ri.pedido_item_id
                   JOIN pedidos_compra pc ON pc.id = pi.pedido_id
                   WHERE pc.obra_id=? AND pi.material_id=?""",
                (obra_id, p["material_id"]),
            )["total"]
        else:
            contagem = query_one(
                "SELECT COUNT(*) AS total FROM patrimonios WHERE obra_atual_id=? AND material_id=?",
                (obra_id, p["material_id"]),
            )["total"]
            adquirida = contagem
            entregue = contagem

        linha["quantidade_adquirida"] = adquirida
        linha["quantidade_entregue"] = entregue
        linha["quantidade_pendente"] = max(p["quantidade_prevista"] - entregue, 0)
        linha["situacao"] = _situacao(p["quantidade_prevista"], entregue)
        linhas.append(linha)
    return linhas


def resumo_materiais_obra(linhas):
    total = len(linhas)
    ok = len([l for l in linhas if l["situacao"] == "OK"])
    parcial = len([l for l in linhas if l["situacao"] == "Parcialmente entregue"])
    pendente = len([l for l in linhas if l["situacao"] == "Pendente"])
    return {"total": total, "ok": ok, "parcial": parcial, "pendente": pendente}


def salvar_material_planejado(obra_id, material_id, quantidade_prevista, observacoes):
    existente = query_one(
        "SELECT id FROM obra_materiais_planejados WHERE obra_id=? AND material_id=?",
        (obra_id, material_id),
    )
    if existente:
        execute(
            "UPDATE obra_materiais_planejados SET quantidade_prevista=?, observacoes=? WHERE id=?",
            (quantidade_prevista, observacoes, existente["id"]),
        )
    else:
        execute(
            """INSERT INTO obra_materiais_planejados (obra_id, material_id, quantidade_prevista, observacoes)
               VALUES (?, ?, ?, ?)""",
            (obra_id, material_id, quantidade_prevista, observacoes),
        )


def remover_material_planejado(item_id, obra_id):
    item = query_one("SELECT id FROM obra_materiais_planejados WHERE id=? AND obra_id=?", (item_id, obra_id))
    if item:
        execute("DELETE FROM obra_materiais_planejados WHERE id=?", (item_id,))
