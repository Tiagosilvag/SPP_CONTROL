from flask import Blueprint, render_template, request, redirect, url_for, flash
from db import query_all, query_one, execute
from services import aplicar_efeito_movimentacao_patrimonio, TIPOS_MOV_PATRIMONIO, QUICK_TIPOS_PATRIMONIO

bp = Blueprint("mov_patrimonio", __name__)


@bp.route("/")
def listar():
    tipo = request.args.get("tipo", "")
    unidade_id = request.args.get("unidade_id", type=int)
    obra_id = request.args.get("obra_id", type=int)
    status_devolucao = request.args.get("status_devolucao", "")
    responsavel = request.args.get("responsavel", "").strip()
    data_inicio = request.args.get("data_inicio", "")
    data_fim = request.args.get("data_fim", "")

    sql = """SELECT mp.*, p.num_patrimonio,
                     uo.nome AS unidade_origem_nome, ud.nome AS unidade_destino_nome,
                     o.descricao AS obra_descricao, uc.nome AS criado_por_nome
              FROM movimentacoes_patrimonio mp
              JOIN patrimonios p ON p.id = mp.patrimonio_id
              LEFT JOIN unidades uo ON uo.id = mp.unidade_origem_id
              LEFT JOIN unidades ud ON ud.id = mp.unidade_destino_id
              LEFT JOIN obras o ON o.id = mp.obra_id
              LEFT JOIN usuarios uc ON uc.id = mp.criado_por
              WHERE 1=1"""
    args = []
    if tipo:
        sql += " AND mp.tipo_movimentacao=?"
        args.append(tipo)
    if unidade_id:
        sql += " AND (mp.unidade_origem_id=? OR mp.unidade_destino_id=?)"
        args.extend([unidade_id, unidade_id])
    if obra_id:
        sql += " AND (mp.obra_id=? OR mp.obra_origem_id=? OR mp.obra_destino_id=?)"
        args.extend([obra_id, obra_id, obra_id])
    if status_devolucao:
        sql += " AND mp.status_devolucao=?"
        args.append(status_devolucao)
    if responsavel:
        sql += " AND mp.responsavel ILIKE ?"
        args.append(f"%{responsavel}%")
    if data_inicio:
        sql += " AND mp.data_movimentacao::date >= ?::date"
        args.append(data_inicio)
    if data_fim:
        sql += " AND mp.data_movimentacao::date <= ?::date"
        args.append(data_fim)
    sql += " ORDER BY mp.data_movimentacao DESC"
    movs = query_all(sql, tuple(args))
    return render_template(
        "mov_patrimonio/list.html",
        movs=movs,
        tipo=tipo,
        tipos=TIPOS_MOV_PATRIMONIO,
        quick_tipos=QUICK_TIPOS_PATRIMONIO,
        unidades=query_all("SELECT * FROM unidades ORDER BY nome"),
        obras=query_all("SELECT * FROM obras ORDER BY descricao"),
        filtros=dict(
            unidade_id=unidade_id, obra_id=obra_id, status_devolucao=status_devolucao,
            responsavel=responsavel, data_inicio=data_inicio, data_fim=data_fim,
        ),
    )


@bp.route("/nova", methods=["GET", "POST"])
def nova():
    patrimonios = query_all(
        """SELECT p.*, m.nome AS material_nome FROM patrimonios p
           JOIN materiais m ON m.id = p.material_id ORDER BY p.num_patrimonio"""
    )
    secretarias = query_all("SELECT * FROM secretarias ORDER BY nome")
    unidades = query_all("SELECT * FROM unidades ORDER BY nome")
    obras = query_all("SELECT * FROM obras ORDER BY descricao")
    tipo_prefill = request.args.get("tipo", "")
    obra_id_prefill = request.args.get("obra_id", type=int)

    if request.method == "POST":
        tipo = request.form["tipo_movimentacao"]
        patrimonio_id = int(request.form["patrimonio_id"])
        patrimonio = query_one("SELECT * FROM patrimonios WHERE id=?", (patrimonio_id,))
        if patrimonio is None:
            flash("Bem patrimonial não encontrado.", "danger")
            return redirect(url_for("mov_patrimonio.nova"))

        if tipo == "Empréstimo" and patrimonio["status"] != "Disponível":
            flash(f'Este bem não está "Disponível" (status atual: {patrimonio["status"]}).', "danger")
            return redirect(url_for("mov_patrimonio.nova"))
        if tipo == "Devolução" and patrimonio["status"] not in ("Emprestado", "Em Uso"):
            flash(f'Este bem não está emprestado/em uso (status atual: {patrimonio["status"]}).', "danger")
            return redirect(url_for("mov_patrimonio.nova"))

        obra_origem_id = request.form.get("obra_origem_id") or None

        mov_id = execute(
            """INSERT INTO movimentacoes_patrimonio
               (data_movimentacao, tipo_movimentacao, patrimonio_id, secretaria_proprietaria_id,
                unidade_origem_id, unidade_destino_id, obra_id, obra_origem_id, obra_destino_id,
                data_prev_devolucao, data_real_devolucao, status_devolucao, responsavel, observacoes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                request.form.get("data_movimentacao"),
                tipo,
                patrimonio_id,
                request.form.get("secretaria_proprietaria_id") or None,
                request.form.get("unidade_origem_id") or None,
                request.form.get("unidade_destino_id") or None,
                obra_origem_id,
                obra_origem_id,
                request.form.get("obra_destino_id") or None,
                request.form.get("data_prev_devolucao") or None,
                request.form.get("data_real_devolucao") or None,
                request.form.get("status_devolucao", "—"),
                request.form.get("responsavel", "").strip(),
                request.form.get("observacoes", "").strip(),
            ),
        )
        aplicar_efeito_movimentacao_patrimonio(mov_id)
        flash("Movimentação de patrimônio registrada com sucesso.", "success")
        return redirect(url_for("mov_patrimonio.listar"))

    return render_template(
        "mov_patrimonio/form.html",
        patrimonios=patrimonios,
        secretarias=secretarias,
        unidades=unidades,
        obras=obras,
        tipos=TIPOS_MOV_PATRIMONIO,
        tipo_prefill=tipo_prefill,
        obra_id_prefill=obra_id_prefill,
    )


@bp.route("/<int:id>/excluir", methods=["POST"])
def excluir(id):
    execute("DELETE FROM movimentacoes_patrimonio WHERE id=?", (id,))
    flash("Movimentação excluída.", "success")
    return redirect(url_for("mov_patrimonio.listar"))
