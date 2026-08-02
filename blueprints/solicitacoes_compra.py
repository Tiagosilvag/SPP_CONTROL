from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from db import query_all, query_one, execute
from services_solicitacoes import STATUS_SOLICITACAO, gerar_numero_solicitacao, itens_solicitacao

bp = Blueprint("solicitacoes_compra", __name__)


def _parse_itens_form():
    materiais = request.form.getlist("item_material_id[]")
    quantidades = request.form.getlist("item_quantidade[]")
    observacoes = request.form.getlist("item_observacoes[]")
    itens = []
    for material_id, quantidade, obs in zip(materiais, quantidades, observacoes):
        if not material_id or not quantidade:
            continue
        itens.append(
            {
                "material_id": int(material_id),
                "quantidade_solicitada": float(quantidade),
                "observacoes": obs.strip(),
            }
        )
    return itens


@bp.route("/")
def listar():
    obra_id = request.args.get("obra_id", type=int)
    status = request.args.get("status", "")

    sql = """SELECT sc.*, o.descricao AS obra_descricao, o.codigo AS obra_codigo
             FROM solicitacoes_compra sc
             JOIN obras o ON o.id = sc.obra_id
             WHERE 1=1"""
    args = []
    if obra_id:
        sql += " AND sc.obra_id=?"
        args.append(obra_id)
    if status:
        sql += " AND sc.status=?"
        args.append(status)
    sql += " ORDER BY sc.id DESC"

    solicitacoes = query_all(sql, tuple(args))
    return render_template(
        "solicitacoes_compra/list.html",
        solicitacoes=solicitacoes,
        obras=query_all("SELECT * FROM obras ORDER BY descricao"),
        status_list=STATUS_SOLICITACAO,
        filtros=dict(obra_id=obra_id, status=status),
    )


@bp.route("/nova", methods=["GET", "POST"])
def nova():
    obra_id_prefill = request.args.get("obra_id", type=int)

    if request.method == "POST":
        itens = _parse_itens_form()
        if not itens:
            flash("Inclua ao menos um material na solicitação.", "danger")
            return redirect(url_for("solicitacoes_compra.nova", obra_id=obra_id_prefill))

        solicitacao_id = execute(
            """INSERT INTO solicitacoes_compra (numero_solicitacao, obra_id, data_solicitacao,
               solicitante, status, observacoes, criado_por)
               VALUES (?, ?, ?, ?, 'Aberta', ?, ?)""",
            (
                gerar_numero_solicitacao(),
                request.form["obra_id"],
                request.form.get("data_solicitacao"),
                request.form.get("solicitante", "").strip(),
                request.form.get("observacoes", "").strip(),
                g.user["id"],
            ),
        )
        for item in itens:
            execute(
                """INSERT INTO solicitacoes_compra_itens (solicitacao_id, material_id,
                   quantidade_solicitada, observacoes) VALUES (?, ?, ?, ?)""",
                (solicitacao_id, item["material_id"], item["quantidade_solicitada"], item["observacoes"]),
            )
        flash("Solicitação de compra cadastrada com sucesso.", "success")
        return redirect(url_for("solicitacoes_compra.detalhe", id=solicitacao_id))

    return render_template(
        "solicitacoes_compra/form.html",
        obra_id_prefill=obra_id_prefill,
        obras=query_all("SELECT * FROM obras WHERE status='Em Andamento' ORDER BY descricao"),
        materiais=query_all("SELECT * FROM materiais WHERE tipo_material='Consumível' AND ativo=1 ORDER BY nome"),
    )


@bp.route("/<int:id>")
def detalhe(id):
    solicitacao = query_one(
        """SELECT sc.*, o.descricao AS obra_descricao, o.codigo AS obra_codigo
           FROM solicitacoes_compra sc JOIN obras o ON o.id = sc.obra_id
           WHERE sc.id=?""",
        (id,),
    )
    if solicitacao is None:
        flash("Solicitação não encontrada.", "danger")
        return redirect(url_for("solicitacoes_compra.listar"))
    pedidos = query_all(
        """SELECT p.* FROM pedidos_compra p WHERE p.solicitacao_id=? ORDER BY p.id DESC""", (id,)
    )
    return render_template(
        "solicitacoes_compra/detalhe.html",
        solicitacao=solicitacao,
        itens=itens_solicitacao(id),
        pedidos=pedidos,
    )


@bp.route("/<int:id>/cancelar", methods=["POST"])
def cancelar(id):
    solicitacao = query_one("SELECT * FROM solicitacoes_compra WHERE id=?", (id,))
    if solicitacao and solicitacao["status"] not in ("Atendida", "Cancelada"):
        execute("UPDATE solicitacoes_compra SET status='Cancelada' WHERE id=?", (id,))
        flash("Solicitação cancelada.", "success")
    return redirect(url_for("solicitacoes_compra.detalhe", id=id))


@bp.route("/<int:id>/excluir", methods=["POST"])
def excluir(id):
    solicitacao = query_one("SELECT * FROM solicitacoes_compra WHERE id=?", (id,))
    if solicitacao and solicitacao["status"] == "Aberta":
        execute("DELETE FROM solicitacoes_compra WHERE id=?", (id,))
        flash("Solicitação excluída.", "success")
    else:
        flash("Só é possível excluir solicitações que ainda não foram atendidas.", "danger")
    return redirect(url_for("solicitacoes_compra.listar"))
