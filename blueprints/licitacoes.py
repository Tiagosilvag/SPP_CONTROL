from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from db import query_all, query_one, execute
from auth import roles_required

bp = Blueprint("licitacoes", __name__)

CATEGORIAS = ["Materiais de Consumo", "Materiais Permanentes", "Serviços", "Obras", "Outros"]
MODALIDADES = ["Pregão Eletrônico", "Pregão Presencial", "Concorrência", "Tomada de Preços", "Dispensa", "Inexigibilidade"]


@bp.route("/")
@roles_required("Administrador", "Gestor")
def listar():
    q = request.args.get("q", "").strip()
    categoria = request.args.get("categoria", "")
    modalidade = request.args.get("modalidade", "")

    sql = """SELECT l.*, uc.nome AS criado_por_nome
             FROM licitacoes l LEFT JOIN usuarios uc ON uc.id = l.criado_por WHERE 1=1"""
    args = []
    if q:
        sql += " AND (objeto ILIKE ? OR processo ILIKE ?)"
        args.extend([f"%{q}%", f"%{q}%"])
    if categoria:
        sql += " AND categoria=?"
        args.append(categoria)
    if modalidade:
        sql += " AND modalidade=?"
        args.append(modalidade)
    sql += " ORDER BY id DESC"

    licitacoes = query_all(sql, tuple(args))
    return render_template(
        "licitacoes/list.html",
        licitacoes=licitacoes,
        categorias=CATEGORIAS,
        modalidades=MODALIDADES,
        q=q,
        categoria=categoria,
        modalidade=modalidade,
    )


@bp.route("/nova", methods=["GET", "POST"])
@roles_required("Administrador", "Gestor")
def nova():
    if request.method == "POST":
        execute(
            """INSERT INTO licitacoes (categoria, modalidade, objeto, processo, valor_estimado,
               valor_homologado, observacoes, criado_por)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                request.form.get("categoria") or None,
                request.form.get("modalidade") or None,
                request.form["objeto"].strip(),
                request.form.get("processo", "").strip(),
                float(request.form.get("valor_estimado") or 0),
                float(request.form["valor_homologado"]) if request.form.get("valor_homologado") else None,
                request.form.get("observacoes", "").strip(),
                g.user["id"],
            ),
        )
        flash("Licitação cadastrada com sucesso.", "success")
        return redirect(url_for("licitacoes.listar"))
    return render_template("licitacoes/form.html", licitacao=None, categorias=CATEGORIAS, modalidades=MODALIDADES)


@bp.route("/<int:id>/editar", methods=["GET", "POST"])
@roles_required("Administrador", "Gestor")
def editar(id):
    l = query_one("SELECT * FROM licitacoes WHERE id=?", (id,))
    if l is None:
        flash("Licitação não encontrada.", "danger")
        return redirect(url_for("licitacoes.listar"))
    if request.method == "POST":
        execute(
            """UPDATE licitacoes SET categoria=?, modalidade=?, objeto=?, processo=?, valor_estimado=?,
               valor_homologado=?, observacoes=? WHERE id=?""",
            (
                request.form.get("categoria") or None,
                request.form.get("modalidade") or None,
                request.form["objeto"].strip(),
                request.form.get("processo", "").strip(),
                float(request.form.get("valor_estimado") or 0),
                float(request.form["valor_homologado"]) if request.form.get("valor_homologado") else None,
                request.form.get("observacoes", "").strip(),
                id,
            ),
        )
        flash("Licitação atualizada com sucesso.", "success")
        return redirect(url_for("licitacoes.listar"))
    return render_template("licitacoes/form.html", licitacao=l, categorias=CATEGORIAS, modalidades=MODALIDADES)


@bp.route("/<int:id>/excluir", methods=["POST"])
@roles_required("Administrador", "Gestor")
def excluir(id):
    execute("DELETE FROM licitacoes WHERE id=?", (id,))
    flash("Licitação excluída.", "success")
    return redirect(url_for("licitacoes.listar"))
