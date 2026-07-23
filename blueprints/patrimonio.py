from flask import Blueprint, render_template, request, redirect, url_for, flash
from db import query_all, query_one, execute

bp = Blueprint("patrimonio", __name__)

ESTADOS = ["Ótimo", "Bom", "Regular", "Danificado"]
STATUS_LIST = ["Disponível", "Em Uso", "Emprestado", "Manutenção"]


@bp.route("/")
def listar():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    sql = """SELECT p.*, m.nome AS material_nome, s.sigla AS secretaria_sigla, u.nome AS unidade_nome
             FROM patrimonios p
             JOIN materiais m ON m.id = p.material_id
             LEFT JOIN secretarias s ON s.id = p.secretaria_proprietaria_id
             LEFT JOIN unidades u ON u.id = p.unidade_atual_id
             WHERE 1=1"""
    args = []
    if q:
        sql += " AND p.num_patrimonio LIKE ?"
        args.append(f"%{q}%")
    if status:
        sql += " AND p.status=?"
        args.append(status)
    sql += " ORDER BY p.num_patrimonio"
    patrimonios = query_all(sql, tuple(args))
    return render_template(
        "patrimonio/list.html", patrimonios=patrimonios, q=q, status=status, status_list=STATUS_LIST
    )


@bp.route("/<int:id>")
def detalhe(id):
    p = query_one(
        """SELECT p.*, m.nome AS material_nome, s.sigla AS secretaria_sigla, u.nome AS unidade_nome
           FROM patrimonios p
           JOIN materiais m ON m.id = p.material_id
           LEFT JOIN secretarias s ON s.id = p.secretaria_proprietaria_id
           LEFT JOIN unidades u ON u.id = p.unidade_atual_id
           WHERE p.id=?""",
        (id,),
    )
    if p is None:
        flash("Bem patrimonial não encontrado.", "danger")
        return redirect(url_for("patrimonio.listar"))
    historico = query_all(
        """SELECT mp.*, uo.nome AS unidade_origem_nome, ud.nome AS unidade_destino_nome
           FROM movimentacoes_patrimonio mp
           LEFT JOIN unidades uo ON uo.id = mp.unidade_origem_id
           LEFT JOIN unidades ud ON ud.id = mp.unidade_destino_id
           WHERE mp.patrimonio_id=? ORDER BY mp.data_movimentacao DESC""",
        (id,),
    )
    return render_template("patrimonio/detalhe.html", p=p, historico=historico)


@bp.route("/novo", methods=["GET", "POST"])
def novo():
    materiais = query_all("SELECT * FROM materiais WHERE tipo_material='Patrimonial' ORDER BY nome")
    secretarias = query_all("SELECT * FROM secretarias ORDER BY nome")
    unidades = query_all("SELECT * FROM unidades ORDER BY nome")
    if request.method == "POST":
        execute(
            """INSERT INTO patrimonios (num_patrimonio, material_id, secretaria_proprietaria_id,
               data_aquisicao, estado_conservacao, unidade_atual_id, status, observacoes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                request.form["num_patrimonio"].strip(),
                request.form["material_id"],
                request.form.get("secretaria_proprietaria_id") or None,
                request.form.get("data_aquisicao") or None,
                request.form.get("estado_conservacao", "Bom"),
                request.form.get("unidade_atual_id") or None,
                request.form.get("status", "Disponível"),
                request.form.get("observacoes", "").strip(),
            ),
        )
        flash("Bem patrimonial cadastrado com sucesso.", "success")
        return redirect(url_for("patrimonio.listar"))
    return render_template(
        "patrimonio/form.html",
        p=None,
        materiais=materiais,
        secretarias=secretarias,
        unidades=unidades,
        estados=ESTADOS,
        status_list=STATUS_LIST,
    )


@bp.route("/<int:id>/editar", methods=["GET", "POST"])
def editar(id):
    p = query_one("SELECT * FROM patrimonios WHERE id=?", (id,))
    if p is None:
        flash("Bem patrimonial não encontrado.", "danger")
        return redirect(url_for("patrimonio.listar"))
    materiais = query_all("SELECT * FROM materiais WHERE tipo_material='Patrimonial' ORDER BY nome")
    secretarias = query_all("SELECT * FROM secretarias ORDER BY nome")
    unidades = query_all("SELECT * FROM unidades ORDER BY nome")
    if request.method == "POST":
        execute(
            """UPDATE patrimonios SET num_patrimonio=?, material_id=?, secretaria_proprietaria_id=?,
               data_aquisicao=?, estado_conservacao=?, unidade_atual_id=?, status=?, observacoes=?
               WHERE id=?""",
            (
                request.form["num_patrimonio"].strip(),
                request.form["material_id"],
                request.form.get("secretaria_proprietaria_id") or None,
                request.form.get("data_aquisicao") or None,
                request.form.get("estado_conservacao", "Bom"),
                request.form.get("unidade_atual_id") or None,
                request.form.get("status", "Disponível"),
                request.form.get("observacoes", "").strip(),
                id,
            ),
        )
        flash("Bem patrimonial atualizado com sucesso.", "success")
        return redirect(url_for("patrimonio.listar"))
    return render_template(
        "patrimonio/form.html",
        p=p,
        materiais=materiais,
        secretarias=secretarias,
        unidades=unidades,
        estados=ESTADOS,
        status_list=STATUS_LIST,
    )


@bp.route("/<int:id>/excluir", methods=["POST"])
def excluir(id):
    execute("DELETE FROM patrimonios WHERE id=?", (id,))
    flash("Bem patrimonial excluído.", "success")
    return redirect(url_for("patrimonio.listar"))
