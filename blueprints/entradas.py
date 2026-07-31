from flask import Blueprint, render_template, request, redirect, url_for, flash
from db import query_all, query_one, execute

bp = Blueprint("entradas", __name__)


@bp.route("/")
def listar():
    secretaria_id = request.args.get("secretaria_id", type=int)
    unidade_id = request.args.get("unidade_id", type=int)
    obra_id = request.args.get("obra_id", type=int)
    fornecedor_id = request.args.get("fornecedor_id", type=int)
    data_inicio = request.args.get("data_inicio", "")
    data_fim = request.args.get("data_fim", "")

    sql = """SELECT e.*, m.nome AS material_nome, m.unidade_medida,
                    s.sigla AS secretaria_sigla, u.nome AS unidade_nome,
                    f.nome AS fornecedor_nome, o.descricao AS obra_descricao,
                    p.numero_pedido, p.id AS pedido_id
             FROM entradas_estoque e
             JOIN materiais m ON m.id = e.material_id
             LEFT JOIN secretarias s ON s.id = e.secretaria_proprietaria_id
             LEFT JOIN unidades u ON u.id = e.unidade_destino_id
             LEFT JOIN fornecedores f ON f.id = e.fornecedor_id
             LEFT JOIN obras o ON o.id = e.obra_id
             LEFT JOIN pedidos_compra_itens pci ON pci.id = e.pedido_item_id
             LEFT JOIN pedidos_compra p ON p.id = pci.pedido_id
             WHERE 1=1"""
    args = []
    if secretaria_id:
        sql += " AND e.secretaria_proprietaria_id=?"
        args.append(secretaria_id)
    if unidade_id:
        sql += " AND e.unidade_destino_id=?"
        args.append(unidade_id)
    if obra_id:
        sql += " AND e.obra_id=?"
        args.append(obra_id)
    if fornecedor_id:
        sql += " AND e.fornecedor_id=?"
        args.append(fornecedor_id)
    if data_inicio:
        sql += " AND e.data_entrada >= ?"
        args.append(data_inicio)
    if data_fim:
        sql += " AND e.data_entrada <= ?"
        args.append(data_fim)
    sql += " ORDER BY e.data_entrada DESC"

    entradas = query_all(sql, tuple(args))
    return render_template(
        "entradas/list.html",
        entradas=entradas,
        secretarias=query_all("SELECT * FROM secretarias ORDER BY nome"),
        unidades=query_all("SELECT * FROM unidades ORDER BY nome"),
        obras=query_all("SELECT * FROM obras ORDER BY descricao"),
        fornecedores=query_all("SELECT * FROM fornecedores ORDER BY nome"),
        filtros=dict(
            secretaria_id=secretaria_id, unidade_id=unidade_id, obra_id=obra_id,
            fornecedor_id=fornecedor_id, data_inicio=data_inicio, data_fim=data_fim,
        ),
    )


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
