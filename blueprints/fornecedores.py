from flask import Blueprint, render_template, request, redirect, url_for, flash
from db import query_all, query_one, execute

bp = Blueprint("fornecedores", __name__)


@bp.route("/")
def listar():
    q = request.args.get("q", "").strip()
    if q:
        fornecedores = query_all("SELECT * FROM fornecedores WHERE nome LIKE ? ORDER BY nome", (f"%{q}%",))
    else:
        fornecedores = query_all("SELECT * FROM fornecedores ORDER BY nome")
    return render_template("fornecedores/list.html", fornecedores=fornecedores, q=q)


@bp.route("/novo", methods=["GET", "POST"])
def novo():
    if request.method == "POST":
        execute(
            "INSERT INTO fornecedores (nome, cnpj, contato, ativo) VALUES (?, ?, ?, ?)",
            (
                request.form["nome"].strip(),
                request.form.get("cnpj", "").strip(),
                request.form.get("contato", "").strip(),
                1 if request.form.get("ativo") else 0,
            ),
        )
        flash("Fornecedor cadastrado com sucesso.", "success")
        return redirect(url_for("fornecedores.listar"))
    return render_template("fornecedores/form.html", fornecedor=None)


@bp.route("/<int:id>/editar", methods=["GET", "POST"])
def editar(id):
    f = query_one("SELECT * FROM fornecedores WHERE id=?", (id,))
    if f is None:
        flash("Fornecedor não encontrado.", "danger")
        return redirect(url_for("fornecedores.listar"))
    if request.method == "POST":
        execute(
            "UPDATE fornecedores SET nome=?, cnpj=?, contato=?, ativo=? WHERE id=?",
            (
                request.form["nome"].strip(),
                request.form.get("cnpj", "").strip(),
                request.form.get("contato", "").strip(),
                1 if request.form.get("ativo") else 0,
                id,
            ),
        )
        flash("Fornecedor atualizado com sucesso.", "success")
        return redirect(url_for("fornecedores.listar"))
    return render_template("fornecedores/form.html", fornecedor=f)


@bp.route("/<int:id>/excluir", methods=["POST"])
def excluir(id):
    execute("DELETE FROM fornecedores WHERE id=?", (id,))
    flash("Fornecedor excluído.", "success")
    return redirect(url_for("fornecedores.listar"))
