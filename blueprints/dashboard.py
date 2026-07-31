from flask import Blueprint, render_template
from services import dashboard_stats
from services_compras import pedidos_atrasados, pedidos_proximos_entrega
from db import query_all

bp = Blueprint("dashboard", __name__)


@bp.route("/")
def index():
    stats = dashboard_stats()

    ultimas_entradas = query_all(
        """SELECT e.*, m.nome AS material_nome, m.unidade_medida, s.sigla AS secretaria_sigla
           FROM entradas_estoque e
           JOIN materiais m ON m.id = e.material_id
           LEFT JOIN secretarias s ON s.id = e.secretaria_proprietaria_id
           ORDER BY e.data_entrada DESC LIMIT 5"""
    )
    ultimos_emprestimos = query_all(
        """SELECT mp.*, p.num_patrimonio
           FROM movimentacoes_patrimonio mp
           JOIN patrimonios p ON p.id = mp.patrimonio_id
           WHERE mp.tipo_movimentacao='Empréstimo'
           ORDER BY mp.data_movimentacao DESC LIMIT 5"""
    )

    atrasados = pedidos_atrasados()
    proximos = pedidos_proximos_entrega()

    grafico_secretaria = query_all(
        """SELECT s.sigla AS label, COUNT(p.id) AS valor
           FROM secretarias s LEFT JOIN patrimonios p ON p.secretaria_proprietaria_id = s.id
           GROUP BY s.sigla ORDER BY valor DESC LIMIT 8"""
    )
    grafico_fornecedor = query_all(
        """SELECT f.nome AS label, COALESCE(SUM(pi.quantidade_solicitada * pi.valor_unitario), 0) AS valor
           FROM fornecedores f
           JOIN pedidos_compra pc ON pc.fornecedor_id = f.id
           JOIN pedidos_compra_itens pi ON pi.pedido_id = pc.id
           GROUP BY f.nome ORDER BY valor DESC LIMIT 8"""
    )
    grafico_obra = query_all(
        """SELECT o.descricao AS label, COUNT(mp.id) AS valor
           FROM obras o LEFT JOIN movimentacoes_patrimonio mp ON mp.obra_id = o.id
           GROUP BY o.descricao ORDER BY valor DESC LIMIT 8"""
    )

    return render_template(
        "dashboard.html",
        stats=stats,
        ultimas_entradas=ultimas_entradas,
        ultimos_emprestimos=ultimos_emprestimos,
        pedidos_atrasados=atrasados[:8],
        pedidos_proximos=proximos[:8],
        grafico_secretaria=grafico_secretaria,
        grafico_fornecedor=grafico_fornecedor,
        grafico_obra=grafico_obra,
    )
