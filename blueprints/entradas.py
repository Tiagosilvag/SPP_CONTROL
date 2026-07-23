from flask import Blueprint, render_template, request, redirect, url_for, flash
from db import query_all, query_one, execute

bp = Blueprint("entradas", __name__)


@bp.route("/")
def listar():
    entradas = query_all(
        """SELECT e.*, m.nome AS material_nome, m.unidade_medida,
                  s.sigla AS secretaria_sigla, u.nome AS unidade_nome,
                  f.nome AS fornecedor_nome, o.descricao AS obra_descricao
           FROM entradas_estoque e
           JOIN materiais m ON m.id = e.material_id
           LEFT JOIN secretarias s ON s.id = e.secretaria_proprietaria_id
           LEFT JOIN unidades u ON u.id = e.unidade_destino_id
           LEFT JOIN fornecedores f ON f.id = e.fornecedor_id
           LEFT JOIN obras o ON o.id = e.obra_id
           ORDER BY e.data_entrada DESC"""
    )
    return render_template("entradas/list.html", entradas=entradas)


@bp.route("/nova", methods=["GET", "POST"])
def nova():
    materiais = query_all(
        "SELECT * FROM materiais WHERE tipo_material='Consumível' AND ativo=1 ORDER BY nome"
    )
    secretarias = query_all("SELECT * FROM secretarias ORDER BY nome")
    unidades = query_all("SELECT * FROM unidades ORDER BY nome")
    fornecedores = query_all("SELECT * FROM fornecedores ORDER BY nome")
    obras = query_all("SELECT * FROM obras ORDER BY descricao")

    if request.method == "POST":
        execute(
            """INSERT INTO entradas_estoque (data_entrada, material_id, secretaria_proprietaria_id,
               unidade_destino_id, fornecedor_id, quantidade, nota_fiscal, obra_id, observacoes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                request.form.get("data_entrada"),
                request.form["material_id"],
                request.form.get("secretaria_proprietaria_id") or None,
                request.form.get("unidade_destino_id") or None,
                request.form.get("fornecedor_id") or None,
                float(request.form["quantidade"]),
                request.form.get("nota_fiscal", "").strip(),
                request.form.get("obra_id") or None,
                request.form.get("observacoes", "").strip(),
            ),
        )
        flash("Entrada de estoque registrada com sucesso.", "success")
        return redirect(url_for("entradas.listar"))

    return render_template(
        "entradas/form.html",
        materiais=materiais,
        secretarias=secretarias,
        unidades=unidades,
        fornecedores=fornecedores,
        obras=obras,
    )


@bp.route("/<int:id>/excluir", methods=["POST"])
def excluir(id):
    execute("DELETE FROM entradas_estoque WHERE id=?", (id,))
    flash("Entrada excluída.", "success")
    return redirect(url_for("entradas.listar"))
