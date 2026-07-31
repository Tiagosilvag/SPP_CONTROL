from flask import Blueprint, render_template, request, redirect, url_for, flash
from db import query_all, query_one, execute
from services import saldo_material_secretaria, TIPOS_MOV_CONSUMIVEL, QUICK_TIPOS_CONSUMIVEL

bp = Blueprint("mov_consumiveis", __name__)


@bp.route("/")
def listar():
    tipo = request.args.get("tipo", "")
    secretaria_id = request.args.get("secretaria_id", type=int)
    unidade_id = request.args.get("unidade_id", type=int)
    obra_id = request.args.get("obra_id", type=int)
    responsavel = request.args.get("responsavel", "").strip()
    data_inicio = request.args.get("data_inicio", "")
    data_fim = request.args.get("data_fim", "")

    sql = """SELECT mc.*, m.nome AS material_nome, m.unidade_medida,
                     uo.nome AS unidade_origem_nome, ud.nome AS unidade_destino_nome,
                     o.descricao AS obra_descricao, uc.nome AS criado_por_nome
              FROM movimentacoes_consumiveis mc
              JOIN materiais m ON m.id = mc.material_id
              LEFT JOIN unidades uo ON uo.id = mc.unidade_origem_id
              LEFT JOIN unidades ud ON ud.id = mc.unidade_destino_id
              LEFT JOIN obras o ON o.id = mc.obra_id
              LEFT JOIN usuarios uc ON uc.id = mc.criado_por
              WHERE 1=1"""
    args = []
    if tipo:
        sql += " AND mc.tipo_movimentacao=?"
        args.append(tipo)
    if secretaria_id:
        sql += " AND mc.secretaria_proprietaria_id=?"
        args.append(secretaria_id)
    if unidade_id:
        sql += " AND (mc.unidade_origem_id=? OR mc.unidade_destino_id=?)"
        args.extend([unidade_id, unidade_id])
    if obra_id:
        sql += " AND (mc.obra_id=? OR mc.obra_origem_id=? OR mc.obra_destino_id=?)"
        args.extend([obra_id, obra_id, obra_id])
    if responsavel:
        sql += " AND mc.responsavel ILIKE ?"
        args.append(f"%{responsavel}%")
    if data_inicio:
        sql += " AND mc.data_movimentacao::date >= ?::date"
        args.append(data_inicio)
    if data_fim:
        sql += " AND mc.data_movimentacao::date <= ?::date"
        args.append(data_fim)
    sql += " ORDER BY mc.data_movimentacao DESC"
    movs = query_all(sql, tuple(args))
    return render_template(
        "mov_consumiveis/list.html",
        movs=movs,
        tipo=tipo,
        tipos=TIPOS_MOV_CONSUMIVEL,
        quick_tipos=QUICK_TIPOS_CONSUMIVEL,
        secretarias=query_all("SELECT * FROM secretarias ORDER BY nome"),
        unidades=query_all("SELECT * FROM unidades ORDER BY nome"),
        obras=query_all("SELECT * FROM obras ORDER BY descricao"),
        filtros=dict(
            secretaria_id=secretaria_id, unidade_id=unidade_id, obra_id=obra_id,
            responsavel=responsavel, data_inicio=data_inicio, data_fim=data_fim,
        ),
    )


@bp.route("/nova", methods=["GET", "POST"])
def nova():
    materiais = query_all(
        "SELECT * FROM materiais WHERE tipo_material='Consumível' AND ativo=1 ORDER BY nome"
    )
    secretarias = query_all("SELECT * FROM secretarias ORDER BY nome")
    unidades = query_all("SELECT * FROM unidades ORDER BY nome")
    obras = query_all("SELECT * FROM obras ORDER BY descricao")
    tipo_prefill = request.args.get("tipo", "")

    if request.method == "POST":
        material_id = int(request.form["material_id"])
        secretaria_id = int(request.form["secretaria_proprietaria_id"])
        quantidade = float(request.form["quantidade"])
        tipo = request.form["tipo_movimentacao"]

        if tipo in ("Consumo em Obra", "Empréstimo", "Transferência"):
            saldo = saldo_material_secretaria(material_id, secretaria_id)
            if quantidade > saldo:
                flash(
                    f"Saldo insuficiente. Disponível: {saldo:g} unidade(s) para este material/secretaria.",
                    "danger",
                )
                return redirect(url_for("mov_consumiveis.nova"))

        status_devolucao = "—"
        if tipo == "Empréstimo":
            status_devolucao = "Pendente"
        elif tipo == "Devolução":
            status_devolucao = "Devolvido"

        execute(
            """INSERT INTO movimentacoes_consumiveis
               (data_movimentacao, tipo_movimentacao, material_id, quantidade, unidade_origem_id,
                unidade_destino_id, secretaria_proprietaria_id, obra_id, obra_origem_id, obra_destino_id,
                data_prev_devolucao, data_real_devolucao, status_devolucao, responsavel, observacoes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                request.form.get("data_movimentacao"),
                tipo,
                material_id,
                quantidade,
                request.form.get("unidade_origem_id") or None,
                request.form.get("unidade_destino_id") or None,
                secretaria_id,
                request.form.get("obra_id") or None,
                request.form.get("obra_origem_id") or None,
                request.form.get("obra_destino_id") or None,
                request.form.get("data_prev_devolucao") or None,
                request.form.get("data_real_devolucao") or None,
                status_devolucao,
                request.form.get("responsavel", "").strip(),
                request.form.get("observacoes", "").strip(),
            ),
        )
        flash("Movimentação registrada com sucesso.", "success")
        return redirect(url_for("mov_consumiveis.listar"))

    return render_template(
        "mov_consumiveis/form.html",
        materiais=materiais,
        secretarias=secretarias,
        unidades=unidades,
        obras=obras,
        tipos=TIPOS_MOV_CONSUMIVEL,
        tipo_prefill=tipo_prefill,
    )


@bp.route("/<int:id>/excluir", methods=["POST"])
def excluir(id):
    execute("DELETE FROM movimentacoes_consumiveis WHERE id=?", (id,))
    flash("Movimentação excluída.", "success")
    return redirect(url_for("mov_consumiveis.listar"))
