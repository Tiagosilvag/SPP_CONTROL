from flask import Blueprint, render_template
from services import dashboard_stats
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
    return render_template(
        "dashboard.html",
        stats=stats,
        ultimas_entradas=ultimas_entradas,
        ultimos_emprestimos=ultimos_emprestimos,
    )
