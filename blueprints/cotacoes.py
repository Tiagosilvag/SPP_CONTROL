from flask import Blueprint, render_template, request, redirect, url_for, flash
from db import query_all, query_one, execute
from services import listar_cotacoes, resumo_cotacoes

bp = Blueprint("cotacoes", __name__)


@bp.route("/")
def listar():
    obra_id = request.args.get("obra_id", type=int)
    q = request.args.get("q", "").strip()
    linhas = listar_cotacoes(obra_id=obra_id, q=q)
    resumo = resumo_cotacoes(linhas)
    obras = query_all("SELECT * FROM obras ORDER BY descricao")
    return render_template(
        "cotacoes/list.html", cotacoes=linhas, resumo=resumo, obras=obras, obra_id=obra_id, q=q
    )


@bp.route("/nova", methods=["GET", "POST"])
def nova():
    obras = query_all("SELECT * FROM obras ORDER BY descricao")
    fornecedores = query_all("SELECT * FROM fornecedores WHERE ativo=1 ORDER BY nome")
    if request.method == "POST":
        execute(
            """INSERT INTO cotacoes (obra_id, fornecedor_id, descricao, valor_cotado,
               valor_economizado, data_cotacao, observacoes)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                request.form["obra_id"],
                request.form.get("fornecedor_id") or None,
                request.form["descricao"].strip(),
                float(request.form.get("valor_cotado") or 0),
                float(request.form.get("valor_economizado") or 0),
                request.form.get("data_cotacao") or None,
                request.form.get("observacoes", "").strip(),
            ),
        )
        flash("Cotação cadastrada com sucesso.", "success")
        return redirect(url_for("cotacoes.listar"))
    return render_template("cotacoes/form.html", cotacao=None, obras=obras, fornecedores=fornecedores)


@bp.route("/<int:id>/editar", methods=["GET", "POST"])
def editar(id):
    c = query_one("SELECT * FROM cotacoes WHERE id=?", (id,))
    if c is None:
        flash("Cotação não encontrada.", "danger")
        return redirect(url_for("cotacoes.listar"))
    obras = query_all("SELECT * FROM obras ORDER BY descricao")
    fornecedores = query_all("SELECT * FROM fornecedores WHERE ativo=1 ORDER BY nome")
    if request.method == "POST":
        execute(
            """UPDATE cotacoes SET obra_id=?, fornecedor_id=?, descricao=?, valor_cotado=?,
               valor_economizado=?, data_cotacao=?, observacoes=? WHERE id=?""",
            (
                request.form["obra_id"],
                request.form.get("fornecedor_id") or None,
                request.form["descricao"].strip(),
                float(request.form.get("valor_cotado") or 0),
                float(request.form.get("valor_economizado") or 0),
                request.form.get("data_cotacao") or None,
                request.form.get("observacoes", "").strip(),
                id,
            ),
        )
        flash("Cotação atualizada com sucesso.", "success")
        return redirect(url_for("cotacoes.listar"))
    return render_template("cotacoes/form.html", cotacao=c, obras=obras, fornecedores=fornecedores)


@bp.route("/<int:id>/excluir", methods=["POST"])
def excluir(id):
    execute("DELETE FROM cotacoes WHERE id=?", (id,))
    flash("Cotação excluída.", "success")
    return redirect(url_for("cotacoes.listar"))
