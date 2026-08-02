"""
Regras de negócio do módulo de Compras: Pedidos de Compra, Recebimento
Parcial, controle de duplicidade e planejamento (atrasos/próximas entregas).
"""
from datetime import date, datetime
from db import query_all, query_one, execute
from services_solicitacoes import dar_baixa_em_solicitacao

STATUS_PEDIDO = ["Em Elaboração", "Enviado", "Parcialmente Recebido", "Recebido", "Cancelado"]


def gerar_numero_pedido():
    """Gera o próximo número sequencial do ano corrente, ex: PC-2026-0001."""
    ano = date.today().year
    ultimo = query_one(
        "SELECT numero_pedido FROM pedidos_compra WHERE numero_pedido LIKE ? ORDER BY id DESC LIMIT 1",
        (f"PC-{ano}-%",),
    )
    proximo = 1
    if ultimo:
        try:
            proximo = int(ultimo["numero_pedido"].split("-")[-1]) + 1
        except (ValueError, IndexError):
            proximo = 1
    return f"PC-{ano}-{proximo:04d}"


def buscar_pedido_semelhante(fornecedor_id, responsavel, data_pedido, material_ids):
    """Procura um pedido não cancelado com mesmo fornecedor, responsável,
    data e ao menos um material em comum — usado no alerta de duplicidade."""
    if not fornecedor_id or not data_pedido or not material_ids:
        return None
    candidatos = query_all(
        """SELECT id, numero_pedido FROM pedidos_compra
           WHERE fornecedor_id=? AND data_pedido=? AND status != 'Cancelado'
             AND lower(trim(responsavel)) = lower(trim(?))""",
        (fornecedor_id, data_pedido, responsavel or ""),
    )
    for c in candidatos:
        itens_existentes = {
            r["material_id"]
            for r in query_all("SELECT material_id FROM pedidos_compra_itens WHERE pedido_id=?", (c["id"],))
        }
        if itens_existentes & set(material_ids):
            return c
    return None


def itens_pedido(pedido_id):
    return query_all(
        """SELECT pi.*, m.nome AS material_nome, m.unidade_medida,
                  (pi.quantidade_solicitada - pi.quantidade_atendida) AS quantidade_pendente
           FROM pedidos_compra_itens pi
           JOIN materiais m ON m.id = pi.material_id
           WHERE pi.pedido_id=?
           ORDER BY pi.id""",
        (pedido_id,),
    )


def atualizar_status_pedido(pedido_id):
    """Recalcula o status do pedido a partir do saldo dos itens: fecha
    automaticamente como 'Recebido' quando tudo foi atendido."""
    pedido = query_one("SELECT status FROM pedidos_compra WHERE id=?", (pedido_id,))
    if pedido is None or pedido["status"] in ("Cancelado", "Em Elaboração"):
        return
    itens = query_all(
        "SELECT quantidade_solicitada, quantidade_atendida FROM pedidos_compra_itens WHERE pedido_id=?",
        (pedido_id,),
    )
    if not itens:
        return
    total_solicitado = sum(i["quantidade_solicitada"] for i in itens)
    total_atendido = sum(i["quantidade_atendida"] for i in itens)
    if total_atendido <= 0:
        novo_status = "Enviado"
    elif total_atendido >= total_solicitado:
        novo_status = "Recebido"
    else:
        novo_status = "Parcialmente Recebido"
    execute("UPDATE pedidos_compra SET status=? WHERE id=?", (novo_status, pedido_id), audit=False)


def registrar_recebimento(pedido_id, data_recebimento, nota_fiscal, responsavel, observacoes, itens, usuario_id):
    """itens: lista de dicts {pedido_item_id, quantidade_recebida}. Cria o
    recebimento, dá baixa no saldo dos itens do pedido, gera a entrada de
    estoque correspondente e atualiza o status do pedido."""
    pedido = query_one("SELECT * FROM pedidos_compra WHERE id=?", (pedido_id,))
    recebimento_id = execute(
        """INSERT INTO recebimentos (pedido_id, data_recebimento, nota_fiscal, responsavel, observacoes, criado_por)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (pedido_id, data_recebimento, nota_fiscal, responsavel, observacoes, usuario_id),
    )

    for item in itens:
        quantidade = item["quantidade_recebida"]
        if quantidade <= 0:
            continue
        pedido_item = query_one(
            "SELECT * FROM pedidos_compra_itens WHERE id=?", (item["pedido_item_id"],)
        )
        execute(
            "INSERT INTO recebimento_itens (recebimento_id, pedido_item_id, quantidade_recebida) VALUES (?, ?, ?)",
            (recebimento_id, item["pedido_item_id"], quantidade),
        )
        execute(
            "UPDATE pedidos_compra_itens SET quantidade_atendida = quantidade_atendida + ? WHERE id=?",
            (quantidade, pedido_item["id"]),
            audit=False,
        )
        execute(
            """INSERT INTO entradas_estoque (data_entrada, material_id, secretaria_proprietaria_id,
               unidade_destino_id, fornecedor_id, quantidade, nota_fiscal, pedido_item_id, obra_id, observacoes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data_recebimento,
                pedido_item["material_id"],
                pedido["secretaria_id"],
                pedido["unidade_id"],
                pedido["fornecedor_id"],
                quantidade,
                nota_fiscal,
                pedido_item["id"],
                pedido["obra_id"],
                f"Recebimento do pedido {pedido['numero_pedido']}",
            ),
        )
        dar_baixa_em_solicitacao(pedido_item, quantidade)

    atualizar_status_pedido(pedido_id)
    return recebimento_id


def pedidos_atrasados():
    """Pedidos enviados/parcialmente recebidos cuja previsão de entrega já passou."""
    hoje = date.today().isoformat()
    return query_all(
        """SELECT p.*, f.nome AS fornecedor_nome,
                  (?::date - p.previsao_entrega::date) AS dias_atraso
           FROM pedidos_compra p
           LEFT JOIN fornecedores f ON f.id = p.fornecedor_id
           WHERE p.status IN ('Enviado', 'Parcialmente Recebido')
             AND p.previsao_entrega IS NOT NULL AND p.previsao_entrega != ''
             AND p.previsao_entrega::date < ?::date
           ORDER BY p.previsao_entrega""",
        (hoje, hoje),
    )


def pedidos_proximos_entrega(dias=7):
    """Pedidos com previsão de entrega nos próximos `dias` dias."""
    hoje = date.today().isoformat()
    return query_all(
        """SELECT p.*, f.nome AS fornecedor_nome
           FROM pedidos_compra p
           LEFT JOIN fornecedores f ON f.id = p.fornecedor_id
           WHERE p.status IN ('Enviado', 'Parcialmente Recebido')
             AND p.previsao_entrega IS NOT NULL AND p.previsao_entrega != ''
             AND p.previsao_entrega::date >= ?::date
             AND p.previsao_entrega::date <= (?::date + make_interval(days => ?))
           ORDER BY p.previsao_entrega""",
        (hoje, hoje, dias),
    )
