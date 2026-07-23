from flask import Blueprint, render_template, request, redirect, url_for, flash
from db import query_all, query_one, execute
from services import aplicar_efeito_movimentacao_patrimonio, TIPOS_MOV_PATRIMONIO

bp = Blueprint("mov_patrimonio", __name__)


@bp.route("/")
def listar():
    tipo = request.args.get("tipo", "")
    sql = """SELECT mp.*, p.num_patrimonio,
                     uo.nome AS unidade_origem_nome, ud.nome AS unidade_destino_nome,
                     o.descricao AS obra_descricao
              FROM movimentacoes_patrimonio mp
              JOIN patrimonios p ON p.id = mp.patrimonio_id
              LEFT JOIN unidades uo ON uo.id = mp.unidade_origem_id
              LEFT JOIN unidades ud ON ud.id = mp.unidade_destino_id
              LEFT JOIN obras o ON o.id = mp.obra_id
              WHERE 1=1"""
    args = []
    if tipo:
        sql += " AND mp.tipo_movimentacao=?"
        args.append(tipo)
    sql += " ORDER BY mp.data_movimentacao DESC"
    movs = query_all(sql, tuple(args))
    return render_template("mov_patrimonio/list.html", movs=movs, tipo=tipo, tipos=TIPOS_MOV_PATRIMONIO)


@bp.route("/nova", methods=["GET", "POST"])
def nova():
    patrimonios = query_all(
        """SELECT p.*, m.nome AS material_nome FROM patrimonios p
           JOIN materiais m ON m.id = p.material_id ORDER BY p.num_patrimonio"""
    )
    secretarias = query_all("SELECT * FROM secretarias ORDER BY nome")
    unidades = query_all("SELECT * FROM unidades ORDER BY nome")
    obras = query_all("SELECT * FROM obras ORDER BY descricao")

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

        mov_id = execute(
            """INSERT INTO movimentacoes_patrimonio
               (data_movimentacao, tipo_movimentacao, patrimonio_id, secretaria_proprietaria_id,
                unidade_origem_id, unidade_destino_id, obra_id, data_prev_devolucao,
                data_real_devolucao, status_devolucao, responsavel, observacoes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                request.form.get("data_movimentacao"),
                tipo,
                patrimonio_id,
                request.form.get("secretaria_proprietaria_id") or None,
                request.form.get("unidade_origem_id") or None,
                request.form.get("unidade_destino_id") or None,
                request.form.get("obra_id") or None,
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
    )


@bp.route("/<int:id>/excluir", methods=["POST"])
def excluir(id):
    execute("DELETE FROM movimentacoes_patrimonio WHERE id=?", (id,))
    flash("Movimentação excluída.", "success")
    return redirect(url_for("mov_patrimonio.listar"))
