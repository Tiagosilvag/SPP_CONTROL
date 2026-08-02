from flask import Blueprint, render_template, request, redirect, url_for, flash
from db import query_all, query_one, execute
from services_obras import (
    STATUS_OBRA,
    materiais_planejados_obra,
    resumo_materiais_obra,
    salvar_material_planejado,
    remover_material_planejado,
)
from services_solicitacoes import solicitacoes_abertas_obra

bp = Blueprint("obras", __name__)


@bp.route("/")
def listar():
    status = request.args.get("status", "")
    secretaria_id = request.args.get("secretaria_id", type=int)
    unidade_id = request.args.get("unidade_id", type=int)
    sql = """SELECT o.*, s.sigla AS secretaria_sigla, u.nome AS unidade_nome, uc.nome AS criado_por_nome
             FROM obras o
             LEFT JOIN secretarias s ON s.id = o.secretaria_solicitante_id
             LEFT JOIN unidades u ON u.id = o.unidade_local_id
             LEFT JOIN usuarios uc ON uc.id = o.criado_por
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
        status_list=STATUS_OBRA,
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
        obra_id = execute(
            """INSERT INTO obras (codigo, descricao, secretaria_solicitante_id, unidade_local_id,
               data_inicio, previsao_termino, data_conclusao, status, fiscal_responsavel, observacoes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                request.form.get("codigo", "").strip(),
                request.form["descricao"].strip(),
                request.form.get("secretaria_solicitante_id") or None,
                request.form.get("unidade_local_id") or None,
                request.form.get("data_inicio") or None,
                request.form.get("previsao_termino") or None,
                request.form.get("data_conclusao") or None,
                request.form.get("status", "Em Andamento"),
                request.form.get("fiscal_responsavel", "").strip(),
                request.form.get("observacoes", "").strip(),
            ),
        )
        flash("Obra cadastrada com sucesso. Agora planeje os materiais necessários.", "success")
        return redirect(url_for("obras.planejamento", id=obra_id))
    return render_template("obras/form.html", obra=None, secretarias=secretarias, unidades=unidades, status_list=STATUS_OBRA)


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
            """UPDATE obras SET codigo=?, descricao=?, secretaria_solicitante_id=?, unidade_local_id=?,
               data_inicio=?, previsao_termino=?, data_conclusao=?, status=?, fiscal_responsavel=?,
               observacoes=? WHERE id=?""",
            (
                request.form.get("codigo", "").strip(),
                request.form["descricao"].strip(),
                request.form.get("secretaria_solicitante_id") or None,
                request.form.get("unidade_local_id") or None,
                request.form.get("data_inicio") or None,
                request.form.get("previsao_termino") or None,
                request.form.get("data_conclusao") or None,
                request.form.get("status", "Em Andamento"),
                request.form.get("fiscal_responsavel", "").strip(),
                request.form.get("observacoes", "").strip(),
                id,
            ),
        )
        flash("Obra atualizada com sucesso.", "success")
        return redirect(url_for("obras.detalhe", id=id))
    return render_template("obras/form.html", obra=o, secretarias=secretarias, unidades=unidades, status_list=STATUS_OBRA)


@bp.route("/<int:id>/excluir", methods=["POST"])
def excluir(id):
    tem_vinculos = query_one(
        """SELECT
             (SELECT COUNT(*) FROM pedidos_compra WHERE obra_id=?) +
             (SELECT COUNT(*) FROM solicitacoes_compra WHERE obra_id=?) +
             (SELECT COUNT(*) FROM obra_materiais_planejados WHERE obra_id=?) AS c""",
        (id, id, id),
    )["c"]
    if tem_vinculos:
        flash("Não é possível excluir: existem pedidos, solicitações ou materiais planejados vinculados a esta obra.", "danger")
        return redirect(url_for("obras.detalhe", id=id))
    execute("DELETE FROM obras WHERE id=?", (id,))
    flash("Obra excluída.", "success")
    return redirect(url_for("obras.listar"))


@bp.route("/<int:id>")
def detalhe(id):
    obra = query_one(
        """SELECT o.*, s.sigla AS secretaria_sigla, s.nome AS secretaria_nome, u.nome AS unidade_nome
           FROM obras o
           LEFT JOIN secretarias s ON s.id = o.secretaria_solicitante_id
           LEFT JOIN unidades u ON u.id = o.unidade_local_id
           WHERE o.id=?""",
        (id,),
    )
    if obra is None:
        flash("Obra não encontrada.", "danger")
        return redirect(url_for("obras.listar"))

    materiais = materiais_planejados_obra(id)
    materiais_consumiveis = [m for m in materiais if m["tipo_material"] == "Consumível"]
    materiais_patrimoniais = [m for m in materiais if m["tipo_material"] == "Patrimonial"]

    pedidos = query_all(
        """SELECT p.*, f.nome AS fornecedor_nome FROM pedidos_compra p
           LEFT JOIN fornecedores f ON f.id = p.fornecedor_id
           WHERE p.obra_id=? ORDER BY p.id DESC LIMIT 8""",
        (id,),
    )
    solicitacoes = query_all(
        "SELECT * FROM solicitacoes_compra WHERE obra_id=? ORDER BY id DESC LIMIT 8", (id,)
    )
    movimentacoes = query_all(
        """SELECT mp.*, p.num_patrimonio FROM movimentacoes_patrimonio mp
           JOIN patrimonios p ON p.id = mp.patrimonio_id
           WHERE mp.obra_id=? OR mp.obra_origem_id=? OR mp.obra_destino_id=?
           ORDER BY mp.data_movimentacao DESC LIMIT 8""",
        (id, id, id),
    )
    patrimonios_alocados = query_all(
        """SELECT p.*, m.nome AS material_nome FROM patrimonios p
           JOIN materiais m ON m.id = p.material_id
           WHERE p.obra_atual_id=? ORDER BY p.num_patrimonio""",
        (id,),
    )

    return render_template(
        "obras/detalhe.html",
        obra=obra,
        materiais_consumiveis=materiais_consumiveis,
        materiais_patrimoniais=materiais_patrimoniais,
        resumo=resumo_materiais_obra(materiais),
        pedidos=pedidos,
        solicitacoes=solicitacoes,
        movimentacoes=movimentacoes,
        patrimonios_alocados=patrimonios_alocados,
        solicitacoes_abertas=solicitacoes_abertas_obra(id),
    )


@bp.route("/<int:id>/planejamento", methods=["GET", "POST"])
def planejamento(id):
    obra = query_one("SELECT * FROM obras WHERE id=?", (id,))
    if obra is None:
        flash("Obra não encontrada.", "danger")
        return redirect(url_for("obras.listar"))

    if request.method == "POST":
        material_id = request.form.get("material_id")
        quantidade = request.form.get("quantidade_prevista")
        if not material_id or not quantidade:
            flash("Selecione o material e informe a quantidade prevista.", "danger")
            return redirect(url_for("obras.planejamento", id=id))
        salvar_material_planejado(
            id, int(material_id), float(quantidade), request.form.get("observacoes", "").strip()
        )
        flash("Material adicionado ao planejamento da obra.", "success")
        return redirect(url_for("obras.planejamento", id=id))

    materiais = materiais_planejados_obra(id)
    return render_template(
        "obras/planejamento.html",
        obra=obra,
        materiais_consumiveis=[m for m in materiais if m["tipo_material"] == "Consumível"],
        materiais_patrimoniais=[m for m in materiais if m["tipo_material"] == "Patrimonial"],
        materiais_disponiveis=query_all("SELECT * FROM materiais WHERE ativo=1 ORDER BY tipo_material, nome"),
    )


@bp.route("/<int:id>/planejamento/<int:item_id>/remover", methods=["POST"])
def planejamento_remover(id, item_id):
    remover_material_planejado(item_id, id)
    flash("Material removido do planejamento.", "success")
    return redirect(url_for("obras.planejamento", id=id))
