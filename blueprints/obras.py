from flask import Blueprint, render_template, request, redirect, url_for, flash
from db import query_all, query_one, execute

bp = Blueprint("obras", __name__)


@bp.route("/")
def listar():
    status = request.args.get("status", "")
    secretaria_id = request.args.get("secretaria_id", type=int)
    unidade_id = request.args.get("unidade_id", type=int)
    sql = """SELECT o.*, s.sigla AS secretaria_sigla, u.nome AS unidade_nome
             FROM obras o
             LEFT JOIN secretarias s ON s.id = o.secretaria_solicitante_id
             LEFT JOIN unidades u ON u.id = o.unidade_local_id
             WHERE 1=1"""
    args = []
    if status:
        sql += " AND o.status=?"
        args.append(status)
    if secretaria_id:
        sql += " AND o.secretaria_solicitante_id=?"
        args.append(secretaria_id)
    if unidade_id:
        sql += " AND o.unidade_local_id=?"
        args.append(unidade_id)
    sql += " ORDER BY o.data_inicio DESC"
    obras = query_all(sql, tuple(args))
    return render_template(
        "obras/list.html",
        obras=obras,
        status=status,
        secretaria_id=secretaria_id,
        unidade_id=unidade_id,
        secretarias=query_all("SELECT * FROM secretarias ORDER BY nome"),
        unidades=query_all("SELECT * FROM unidades ORDER BY nome"),
    )


@bp.route("/nova", methods=["GET", "POST"])
def nova():
    secretarias = query_all("SELECT * FROM secretarias ORDER BY nome")
    unidades = query_all("SELECT * FROM unidades ORDER BY nome")
    if request.method == "POST":
        execute(
            """INSERT INTO obras (descricao, secretaria_solicitante_id, unidade_local_id, data_inicio,
               previsao_termino, status, fiscal_responsavel, observacoes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                request.form["descricao"].strip(),
                request.form.get("secretaria_solicitante_id") or None,
                request.form.get("unidade_local_id") or None,
                request.form.get("data_inicio") or None,
                request.form.get("previsao_termino") or None,
                request.form.get("status", "Em Andamento"),
                request.form.get("fiscal_responsavel", "").strip(),
                request.form.get("observacoes", "").strip(),
            ),
        )
        flash("Obra cadastrada com sucesso.", "success")
        return redirect(url_for("obras.listar"))
    return render_template("obras/form.html", obra=None, secretarias=secretarias, unidades=unidades)


@bp.route("/<int:id>/editar", methods=["GET", "POST"])
def editar(id):
    o = query_one("SELECT * FROM obras WHERE id=?", (id,))
    if o is None:
        flash("Obra não encontrada.", "danger")
        return redirect(url_for("obras.listar"))
    secretarias = query_all("SELECT * FROM secretarias ORDER BY nome")
    unidades = query_all("SELECT * FROM unidades ORDER BY nome")
    if request.method == "POST":
        execute(
            """UPDATE obras SET descricao=?, secretaria_solicitante_id=?, unidade_local_id=?, data_inicio=?,
               previsao_termino=?, status=?, fiscal_responsavel=?, observacoes=? WHERE id=?""",
            (
                request.form["descricao"].strip(),
                request.form.get("secretaria_solicitante_id") or None,
                request.form.get("unidade_local_id") or None,
                request.form.get("data_inicio") or None,
                request.form.get("previsao_termino") or None,
                request.form.get("status", "Em Andamento"),
                request.form.get("fiscal_responsavel", "").strip(),
                request.form.get("observacoes", "").strip(),
                id,
            ),
        )
        flash("Obra atualizada com sucesso.", "success")
        return redirect(url_for("obras.listar"))
    return render_template("obras/form.html", obra=o, secretarias=secretarias, unidades=unidades)


@bp.route("/<int:id>/excluir", methods=["POST"])
def excluir(id):
    execute("DELETE FROM obras WHERE id=?", (id,))
    flash("Obra excluída.", "success")
    return redirect(url_for("obras.listar"))
