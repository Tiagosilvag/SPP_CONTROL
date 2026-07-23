from flask import Blueprint, render_template, request, redirect, url_for, flash
from db import query_all, query_one, execute

bp = Blueprint("unidades", __name__)


@bp.route("/")
def listar():
    secretaria_id = request.args.get("secretaria_id", type=int)
    sql = """SELECT u.*, s.sigla AS secretaria_sigla, s.nome AS secretaria_nome
              FROM unidades u LEFT JOIN secretarias s ON s.id = u.secretaria_id"""
    args = ()
    if secretaria_id:
        sql += " WHERE u.secretaria_id=?"
        args = (secretaria_id,)
    sql += " ORDER BY u.nome"
    unidades = query_all(sql, args)
    secretarias = query_all("SELECT * FROM secretarias ORDER BY nome")
    return render_template(
        "unidades/list.html", unidades=unidades, secretarias=secretarias, secretaria_id=secretaria_id
    )


@bp.route("/nova", methods=["GET", "POST"])
def nova():
    secretarias = query_all("SELECT * FROM secretarias ORDER BY nome")
    if request.method == "POST":
        execute(
            """INSERT INTO unidades (secretaria_id, nome, endereco, responsavel_local, ativa)
               VALUES (?, ?, ?, ?, ?)""",
            (
                request.form["secretaria_id"],
                request.form["nome"].strip(),
                request.form.get("endereco", "").strip(),
                request.form.get("responsavel_local", "").strip(),
                1 if request.form.get("ativa") else 0,
            ),
        )
        flash("Unidade cadastrada com sucesso.", "success")
        return redirect(url_for("unidades.listar"))
    return render_template("unidades/form.html", unidade=None, secretarias=secretarias)


@bp.route("/<int:id>/editar", methods=["GET", "POST"])
def editar(id):
    u = query_one("SELECT * FROM unidades WHERE id=?", (id,))
    if u is None:
        flash("Unidade não encontrada.", "danger")
        return redirect(url_for("unidades.listar"))
    secretarias = query_all("SELECT * FROM secretarias ORDER BY nome")
    if request.method == "POST":
        execute(
            """UPDATE unidades SET secretaria_id=?, nome=?, endereco=?, responsavel_local=?, ativa=? WHERE id=?""",
            (
                request.form["secretaria_id"],
                request.form["nome"].strip(),
                request.form.get("endereco", "").strip(),
                request.form.get("responsavel_local", "").strip(),
                1 if request.form.get("ativa") else 0,
                id,
            ),
        )
        flash("Unidade atualizada com sucesso.", "success")
        return redirect(url_for("unidades.listar"))
    return render_template("unidades/form.html", unidade=u, secretarias=secretarias)


@bp.route("/<int:id>/excluir", methods=["POST"])
def excluir(id):
    execute("DELETE FROM unidades WHERE id=?", (id,))
    flash("Unidade excluída.", "success")
    return redirect(url_for("unidades.listar"))
