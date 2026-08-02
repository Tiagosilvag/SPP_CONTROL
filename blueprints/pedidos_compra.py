from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from db import query_all, query_one, execute
from auth import roles_required
from services_compras import (
    STATUS_PEDIDO,
    gerar_numero_pedido,
    buscar_pedido_semelhante,
    itens_pedido,
    registrar_recebimento,
    pedidos_atrasados,
    pedidos_proximos_entrega,
)
from services_solicitacoes import solicitacoes_abertas_obra, itens_solicitacao

bp = Blueprint("pedidos_compra", __name__)


def _parse_itens_form():
    materiais = request.form.getlist("item_material_id[]")
    quantidades = request.form.getlist("item_quantidade[]")
    valores = request.form.getlist("item_valor_unitario[]")
    observacoes = request.form.getlist("item_observacoes[]")
    solicitacao_item_ids = request.form.getlist("item_solicitacao_item_id[]")
    if len(solicitacao_item_ids) != len(materiais):
        solicitacao_item_ids = [""] * len(materiais)
    itens = []
    for material_id, quantidade, valor, obs, sol_item_id in zip(
        materiais, quantidades, valores, observacoes, solicitacao_item_ids
    ):
        if not material_id or not quantidade:
            continue
        itens.append(
            {
                "material_id": int(material_id),
                "quantidade_solicitada": float(quantidade),
                "valor_unitario": float(valor or 0),
                "observacoes": obs.strip(),
                "solicitacao_item_id": int(sol_item_id) if sol_item_id else None,
            }
        )
    return itens


def _form_context(pedido=None, itens=None, obra_id_prefill=None, solicitacao_id_prefill=None):
    obra_id_prefill = obra_id_prefill or (pedido.get("obra_id") if pedido else None)
    return {
        "pedido": pedido,
        "itens": itens or [],
        "secretarias": query_all("SELECT * FROM secretarias WHERE ativa=1 ORDER BY nome"),
        "unidades": query_all("SELECT * FROM unidades WHERE ativa=1 ORDER BY nome"),
        "fornecedores": query_all("SELECT * FROM fornecedores WHERE ativo=1 ORDER BY nome"),
        "materiais": query_all("SELECT * FROM materiais WHERE ativo=1 ORDER BY nome"),
        "obras": query_all("SELECT * FROM obras ORDER BY descricao"),
        "obra_id_prefill": obra_id_prefill,
        "solicitacao_id_prefill": solicitacao_id_prefill,
        "solicitacoes_obra": solicitacoes_abertas_obra(obra_id_prefill) if obra_id_prefill else [],
    }


@bp.route("/")
@roles_required("Administrador", "Gestor")
def listar():
    secretaria_id = request.args.get("secretaria_id", type=int)
    unidade_id = request.args.get("unidade_id", type=int)
    fornecedor_id = request.args.get("fornecedor_id", type=int)
    obra_id = request.args.get("obra_id", type=int)
    status = request.args.get("status", "")
    responsavel = request.args.get("responsavel", "").strip()
    data_inicio = request.args.get("data_inicio", "")
    data_fim = request.args.get("data_fim", "")

    sql = """SELECT p.*, s.sigla AS secretaria_sigla, u.nome AS unidade_nome, f.nome AS fornecedor_nome,
                    uc.nome AS criado_por_nome, o.descricao AS obra_descricao, o.codigo AS obra_codigo
             FROM pedidos_compra p
             LEFT JOIN secretarias s ON s.id = p.secretaria_id
             LEFT JOIN unidades u ON u.id = p.unidade_id
             LEFT JOIN fornecedores f ON f.id = p.fornecedor_id
             LEFT JOIN usuarios uc ON uc.id = p.criado_por
             LEFT JOIN obras o ON o.id = p.obra_id
             WHERE 1=1"""
    args = []
    if obra_id:
        sql += " AND p.obra_id=?"
        args.append(obra_id)
    if secretaria_id:
        sql += " AND p.secretaria_id=?"
        args.append(secretaria_id)
    if unidade_id:
        sql += " AND p.unidade_id=?"
        args.append(unidade_id)
    if fornecedor_id:
        sql += " AND p.fornecedor_id=?"
        args.append(fornecedor_id)
    if status:
        sql += " AND p.status=?"
        args.append(status)
    if responsavel:
        sql += " AND p.responsavel ILIKE ?"
        args.append(f"%{responsavel}%")
    if data_inicio:
        sql += " AND p.data_pedido >= ?"
        args.append(data_inicio)
    if data_fim:
        sql += " AND p.data_pedido <= ?"
        args.append(data_fim)
    sql += " ORDER BY p.id DESC"

    pedidos = query_all(sql, tuple(args))
    return render_template(
        "pedidos_compra/list.html",
        pedidos=pedidos,
        total_atrasados=len(pedidos_atrasados()),
        total_proximos=len(pedidos_proximos_entrega()),
        secretarias=query_all("SELECT * FROM secretarias ORDER BY nome"),
        unidades=query_all("SELECT * FROM unidades ORDER BY nome"),
        fornecedores=query_all("SELECT * FROM fornecedores ORDER BY nome"),
        obras=query_all("SELECT * FROM obras ORDER BY descricao"),
        status_list=STATUS_PEDIDO,
        filtros=dict(
            secretaria_id=secretaria_id, unidade_id=unidade_id, fornecedor_id=fornecedor_id,
            obra_id=obra_id, status=status, responsavel=responsavel, data_inicio=data_inicio, data_fim=data_fim,
        ),
    )


@bp.route("/novo", methods=["GET", "POST"])
@roles_required("Administrador", "Gestor")
def novo():
    if request.method == "POST":
        itens = _parse_itens_form()
        if not itens:
            flash("Inclua ao menos um item no pedido.", "danger")
            return render_template("pedidos_compra/form.html", **_form_context())

        fornecedor_id = request.form.get("fornecedor_id") or None
        data_pedido = request.form.get("data_pedido")
        responsavel = request.form.get("responsavel", "").strip()
        obra_id = request.form.get("obra_id") or None
        solicitacao_id = request.form.get("solicitacao_id") or None
        confirmado = request.form.get("confirmar_duplicidade") == "1"

        if not confirmado:
            semelhante = buscar_pedido_semelhante(
                fornecedor_id, responsavel, data_pedido, [i["material_id"] for i in itens]
            )
            if semelhante:
                flash(
                    f"Já existe um pedido semelhante (mesmo fornecedor, responsável, data e "
                    f"materiais em comum): {semelhante['numero_pedido']}. Revise antes de salvar "
                    f"novamente, ou confirme para salvar mesmo assim.",
                    "warning",
                )
                ctx = _form_context(pedido=request.form, itens=itens, obra_id_prefill=obra_id, solicitacao_id_prefill=solicitacao_id)
                ctx["duplicado"] = True
                return render_template("pedidos_compra/form.html", **ctx)

        pedido_id = execute(
            """INSERT INTO pedidos_compra (numero_pedido, data_pedido, secretaria_id, unidade_id,
               fornecedor_id, responsavel, status, previsao_entrega, observacoes, obra_id,
               solicitacao_id, criado_por)
               VALUES (?, ?, ?, ?, ?, ?, 'Em Elaboração', ?, ?, ?, ?, ?)""",
            (
                gerar_numero_pedido(),
                data_pedido,
                request.form.get("secretaria_id") or None,
                request.form.get("unidade_id") or None,
                fornecedor_id,
                responsavel,
                request.form.get("previsao_entrega") or None,
                request.form.get("observacoes", "").strip(),
                obra_id,
                solicitacao_id,
                g.user["id"],
            ),
        )
        for item in itens:
            execute(
                """INSERT INTO pedidos_compra_itens (pedido_id, material_id, quantidade_solicitada,
                   valor_unitario, observacoes, solicitacao_item_id) VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    pedido_id, item["material_id"], item["quantidade_solicitada"],
                    item["valor_unitario"], item["observacoes"], item["solicitacao_item_id"],
                ),
            )
        flash("Pedido de compra cadastrado com sucesso.", "success")
        return redirect(url_for("pedidos_compra.detalhe", id=pedido_id))

    obra_id_prefill = request.args.get("obra_id", type=int)
    solicitacao_id_prefill = request.args.get("solicitacao_id", type=int)
    itens_prefill = []
    if solicitacao_id_prefill:
        for i in itens_solicitacao(solicitacao_id_prefill):
            if i["quantidade_pendente"] > 0:
                itens_prefill.append(
                    {
                        "material_id": i["material_id"],
                        "material_nome": i["material_nome"],
                        "quantidade_solicitada": i["quantidade_pendente"],
                        "valor_unitario": 0,
                        "observacoes": "",
                        "solicitacao_item_id": i["id"],
                    }
                )
    return render_template(
        "pedidos_compra/form.html",
        **_form_context(itens=itens_prefill, obra_id_prefill=obra_id_prefill, solicitacao_id_prefill=solicitacao_id_prefill),
    )


@bp.route("/<int:id>")
@roles_required("Administrador", "Gestor")
def detalhe(id):
    pedido = query_one(
        """SELECT p.*, s.sigla AS secretaria_sigla, u.nome AS unidade_nome, f.nome AS fornecedor_nome,
                  uc.nome AS criado_por_nome, o.descricao AS obra_descricao, o.codigo AS obra_codigo,
                  sc.numero_solicitacao
           FROM pedidos_compra p
           LEFT JOIN secretarias s ON s.id = p.secretaria_id
           LEFT JOIN unidades u ON u.id = p.unidade_id
           LEFT JOIN fornecedores f ON f.id = p.fornecedor_id
           LEFT JOIN usuarios uc ON uc.id = p.criado_por
           LEFT JOIN obras o ON o.id = p.obra_id
           LEFT JOIN solicitacoes_compra sc ON sc.id = p.solicitacao_id
           WHERE p.id=?""",
        (id,),
    )
    if pedido is None:
        flash("Pedido não encontrado.", "danger")
        return redirect(url_for("pedidos_compra.listar"))
    itens = itens_pedido(id)
    recebimentos = query_all(
        """SELECT r.*, uc.nome AS criado_por_nome FROM recebimentos r
           LEFT JOIN usuarios uc ON uc.id = r.criado_por
           WHERE r.pedido_id=? ORDER BY r.data_recebimento DESC, r.id DESC""",
        (id,),
    )
    return render_template("pedidos_compra/detalhe.html", pedido=pedido, itens=itens, recebimentos=recebimentos)


@bp.route("/<int:id>/editar", methods=["GET", "POST"])
@roles_required("Administrador", "Gestor")
def editar(id):
    pedido = query_one("SELECT * FROM pedidos_compra WHERE id=?", (id,))
    if pedido is None:
        flash("Pedido não encontrado.", "danger")
        return redirect(url_for("pedidos_compra.listar"))
    if pedido["status"] != "Em Elaboração":
        flash("Só é possível editar pedidos que ainda estão em elaboração.", "danger")
        return redirect(url_for("pedidos_compra.detalhe", id=id))

    if request.method == "POST":
        itens = _parse_itens_form()
        if not itens:
            flash("Inclua ao menos um item no pedido.", "danger")
            return redirect(url_for("pedidos_compra.editar", id=id))

        execute(
            """UPDATE pedidos_compra SET data_pedido=?, secretaria_id=?, unidade_id=?, fornecedor_id=?,
               responsavel=?, previsao_entrega=?, observacoes=? WHERE id=?""",
            (
                request.form.get("data_pedido"),
                request.form.get("secretaria_id") or None,
                request.form.get("unidade_id") or None,
                request.form.get("fornecedor_id") or None,
                request.form.get("responsavel", "").strip(),
                request.form.get("previsao_entrega") or None,
                request.form.get("observacoes", "").strip(),
                id,
            ),
        )
        execute("DELETE FROM pedidos_compra_itens WHERE pedido_id=?", (id,), audit=False)
        for item in itens:
            execute(
                """INSERT INTO pedidos_compra_itens (pedido_id, material_id, quantidade_solicitada,
                   valor_unitario, observacoes, solicitacao_item_id) VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    id, item["material_id"], item["quantidade_solicitada"],
                    item["valor_unitario"], item["observacoes"], item["solicitacao_item_id"],
                ),
            )
        flash("Pedido atualizado com sucesso.", "success")
        return redirect(url_for("pedidos_compra.detalhe", id=id))

    return render_template("pedidos_compra/form.html", **_form_context(pedido=pedido, itens=itens_pedido(id)))


@bp.route("/<int:id>/enviar", methods=["POST"])
@roles_required("Administrador", "Gestor")
def enviar(id):
    pedido = query_one("SELECT * FROM pedidos_compra WHERE id=?", (id,))
    if pedido and pedido["status"] == "Em Elaboração":
        execute("UPDATE pedidos_compra SET status='Enviado' WHERE id=?", (id,))
        flash("Pedido enviado ao fornecedor.", "success")
    return redirect(url_for("pedidos_compra.detalhe", id=id))


@bp.route("/<int:id>/cancelar", methods=["POST"])
@roles_required("Administrador", "Gestor")
def cancelar(id):
    pedido = query_one("SELECT * FROM pedidos_compra WHERE id=?", (id,))
    if pedido and pedido["status"] not in ("Recebido", "Cancelado"):
        execute("UPDATE pedidos_compra SET status='Cancelado' WHERE id=?", (id,))
        flash("Pedido cancelado.", "success")
    return redirect(url_for("pedidos_compra.detalhe", id=id))


@bp.route("/<int:id>/excluir", methods=["POST"])
@roles_required("Administrador", "Gestor")
def excluir(id):
    pedido = query_one("SELECT * FROM pedidos_compra WHERE id=?", (id,))
    if pedido and pedido["status"] == "Em Elaboração":
        execute("DELETE FROM pedidos_compra WHERE id=?", (id,))
        flash("Pedido excluído.", "success")
    else:
        flash("Só é possível excluir pedidos que ainda estão em elaboração.", "danger")
    return redirect(url_for("pedidos_compra.listar"))


@bp.route("/<int:id>/recebimento/novo", methods=["GET", "POST"])
@roles_required("Administrador", "Gestor")
def novo_recebimento(id):
    pedido = query_one("SELECT * FROM pedidos_compra WHERE id=?", (id,))
    if pedido is None:
        flash("Pedido não encontrado.", "danger")
        return redirect(url_for("pedidos_compra.listar"))
    if pedido["status"] not in ("Enviado", "Parcialmente Recebido"):
        flash("Este pedido não está disponível para recebimento.", "danger")
        return redirect(url_for("pedidos_compra.detalhe", id=id))

    itens = itens_pedido(id)

    if request.method == "POST":
        itens_recebidos = []
        for item in itens:
            quantidade = request.form.get(f"recebido_quantidade_{item['id']}", "").strip()
            if quantidade and float(quantidade) > 0:
                itens_recebidos.append({"pedido_item_id": item["id"], "quantidade_recebida": float(quantidade)})

        if not itens_recebidos:
            flash("Informe a quantidade recebida de ao menos um item.", "danger")
            return redirect(url_for("pedidos_compra.novo_recebimento", id=id))

        registrar_recebimento(
            pedido_id=id,
            data_recebimento=request.form.get("data_recebimento"),
            nota_fiscal=request.form.get("nota_fiscal", "").strip(),
            responsavel=request.form.get("responsavel", "").strip(),
            observacoes=request.form.get("observacoes", "").strip(),
            itens=itens_recebidos,
            usuario_id=g.user["id"],
        )
        flash("Recebimento registrado com sucesso.", "success")
        return redirect(url_for("pedidos_compra.detalhe", id=id))

    return render_template("pedidos_compra/recebimento_form.html", pedido=pedido, itens=itens)
