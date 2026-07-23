from flask import Blueprint, render_template, request, redirect, url_for, flash
from db import query_all, query_one, execute

bp = Blueprint("materiais", __name__)

CATEGORIAS = ["Construção", "Pintura", "Elétrico", "Hidráulico", "Ferramentas", "Equipamentos", "Outros"]


@bp.route("/")
def listar():
    q = request.args.get("q", "").strip()
    tipo = request.args.get("tipo", "")
    sql = "SELECT * FROM materiais WHERE 1=1"
    args = []
    if q:
        sql += " AND nome LIKE ?"
        args.append(f"%{q}%")
    if tipo:
        sql += " AND tipo_material=?"
        args.append(tipo)
    sql += " ORDER BY nome"
    materiais = query_all(sql, tuple(args))
    return render_template("materiais/list.html", materiais=materiais, q=q, tipo=tipo)


@bp.route("/novo", methods=["GET", "POST"])
def novo():
    if request.method == "POST":
        execute(
            """INSERT INTO materiais (nome, tipo_material, categoria, unidade_medida, estoque_minimo, ativo)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                request.form["nome"].strip(),
                request.form["tipo_material"],
                request.form.get("categoria", "").strip(),
                request.form.get("unidade_medida", "").strip(),
                float(request.form.get("estoque_minimo") or 0),
                1 if request.form.get("ativo") else 0,
            ),
        )
        flash("Material cadastrado com sucesso.", "success")
        return redirect(url_for("materiais.listar"))
    return render_template("materiais/form.html", material=None, categorias=CATEGORIAS)


@bp.route("/<int:id>/editar", methods=["GET", "POST"])
def editar(id):
    m = query_one("SELECT * FROM materiais WHERE id=?", (id,))
    if m is None:
        flash("Material não encontrado.", "danger")
        return redirect(url_for("materiais.listar"))
    if request.method == "POST":
        execute(
            """UPDATE materiais SET nome=?, tipo_material=?, categoria=?, unidade_medida=?,
               estoque_minimo=?, ativo=? WHERE id=?""",
            (
                request.form["nome"].strip(),
                request.form["tipo_material"],
                request.form.get("categoria", "").strip(),
                request.form.get("unidade_medida", "").strip(),
                float(request.form.get("estoque_minimo") or 0),
                1 if request.form.get("ativo") else 0,
                id,
            ),
        )
        flash("Material atualizado com sucesso.", "success")
        return redirect(url_for("materiais.listar"))
    return render_template("materiais/form.html", material=m, categorias=CATEGORIAS)


@bp.route("/<int:id>/excluir", methods=["POST"])
def excluir(id):
    execute("DELETE FROM materiais WHERE id=?", (id,))
    flash("Material excluído.", "success")
    return redirect(url_for("materiais.listar"))
