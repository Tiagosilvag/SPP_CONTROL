from flask import Blueprint, render_template, request, redirect, url_for, flash
from db import query_all, query_one, execute

bp = Blueprint("secretarias", __name__)


@bp.route("/")
def listar():
    q = request.args.get("q", "").strip()
    if q:
        secretarias = query_all(
            "SELECT * FROM secretarias WHERE nome LIKE ? OR sigla LIKE ? ORDER BY nome",
            (f"%{q}%", f"%{q}%"),
        )
    else:
        secretarias = query_all("SELECT * FROM secretarias ORDER BY nome")
    return render_template("secretarias/list.html", secretarias=secretarias, q=q)


@bp.route("/nova", methods=["GET", "POST"])
def nova():
    if request.method == "POST":
        execute(
            """INSERT INTO secretarias (nome, sigla, responsavel, contato, ativa)
               VALUES (?, ?, ?, ?, ?)""",
            (
                request.form["nome"].strip(),
                request.form["sigla"].strip(),
                request.form.get("responsavel", "").strip(),
                request.form.get("contato", "").strip(),
                1 if request.form.get("ativa") else 0,
            ),
        )
        flash("Secretaria cadastrada com sucesso.", "success")
        return redirect(url_for("secretarias.listar"))
    return render_template("secretarias/form.html", secretaria=None)


@bp.route("/<int:id>/editar", methods=["GET", "POST"])
def editar(id):
    s = query_one("SELECT * FROM secretarias WHERE id=?", (id,))
    if s is None:
        flash("Secretaria não encontrada.", "danger")
        return redirect(url_for("secretarias.listar"))
    if request.method == "POST":
        execute(
            """UPDATE secretarias SET nome=?, sigla=?, responsavel=?, contato=?, ativa=? WHERE id=?""",
            (
                request.form["nome"].strip(),
                request.form["sigla"].strip(),
                request.form.get("responsavel", "").strip(),
                request.form.get("contato", "").strip(),
                1 if request.form.get("ativa") else 0,
                id,
            ),
        )
        flash("Secretaria atualizada com sucesso.", "success")
        return redirect(url_for("secretarias.listar"))
    return render_template("secretarias/form.html", secretaria=s)


@bp.route("/<int:id>/excluir", methods=["POST"])
def excluir(id):
    vinculadas = query_one("SELECT COUNT(*) AS c FROM unidades WHERE secretaria_id=?", (id,))["c"]
    if vinculadas:
        flash("Não é possível excluir: existem unidades vinculadas a esta secretaria.", "danger")
        return redirect(url_for("secretarias.listar"))
    execute("DELETE FROM secretarias WHERE id=?", (id,))
    flash("Secretaria excluída.", "success")
    return redirect(url_for("secretarias.listar"))
