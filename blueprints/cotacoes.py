from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from db import query_all, query_one, execute
from services_cotacoes import listar_cotacoes, resumo_cotacoes, itens_cotacao

bp = Blueprint("cotacoes", __name__)

CATEGORIAS = ["Materiais de Consumo", "Materiais Permanentes", "Serviços", "Obras", "Outros"]
MODALIDADES = ["Pregão Eletrônico", "Pregão Presencial", "Dispensa", "Inexigibilidade", "Cotação Direta"]


def _parse_itens_form():
    fornecedores = request.form.getlist("item_fornecedor_id[]")
    valores = request.form.getlist("item_valor_cotado[]")
    observacoes = request.form.getlist("item_observacoes[]")
    vencedor_idx = request.form.get("item_vencedor")
    itens = []
    for i, (fornecedor_id, valor, obs) in enumerate(zip(fornecedores, valores, observacoes)):
        if not fornecedor_id or not valor:
            continue
        itens.append(
            {
                "fornecedor_id": int(fornecedor_id),
                "valor_cotado": float(valor),
                "observacoes": obs.strip(),
                "vencedor": 1 if vencedor_idx == str(i) else 0,
            }
        )
    return itens


@bp.route("/")
def listar():
    obra_id = request.args.get("obra_id", type=int)
    q = request.args.get("q", "").strip()
    categoria = request.args.get("categoria", "")
    modalidade = request.args.get("modalidade", "")
    linhas = listar_cotacoes(obra_id=obra_id, q=q, categoria=categoria, modalidade=modalidade)
    resumo = resumo_cotacoes(linhas)
    obras = query_all("SELECT * FROM obras ORDER BY descricao")
    return render_template(
        "cotacoes/list.html",
        cotacoes=linhas,
        resumo=resumo,
        obras=obras,
        obra_id=obra_id,
        q=q,
        categoria=categoria,
        modalidade=modalidade,
        categorias=CATEGORIAS,
        modalidades=MODALIDADES,
    )


@bp.route("/nova", methods=["GET", "POST"])
def nova():
    obras = query_all("SELECT * FROM obras ORDER BY descricao")
    fornecedores = query_all("SELECT * FROM fornecedores WHERE ativo=1 ORDER BY nome")
    if request.method == "POST":
        itens = _parse_itens_form()
        if not itens:
            flash("Inclua ao menos um fornecedor para comparar.", "danger")
            return render_template(
                "cotacoes/form.html", cotacao=None, itens=[], obras=obras, fornecedores=fornecedores,
                categorias=CATEGORIAS, modalidades=MODALIDADES,
            )
        cotacao_id = execute(
            """INSERT INTO cotacoes (obra_id, descricao, categoria, modalidade, base_legal,
               numero_licitacao, valor_estimado, data_cotacao, observacoes, criado_por)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                request.form["obra_id"],
                request.form["descricao"].strip(),
                request.form.get("categoria") or None,
                request.form.get("modalidade") or None,
                request.form.get("base_legal", "").strip(),
                request.form.get("numero_licitacao", "").strip(),
                float(request.form.get("valor_estimado") or 0),
                request.form.get("data_cotacao") or None,
                request.form.get("observacoes", "").strip(),
                g.user["id"],
            ),
        )
        for item in itens:
            execute(
                """INSERT INTO cotacoes_itens (cotacao_id, fornecedor_id, valor_cotado, vencedor, observacoes)
                   VALUES (?, ?, ?, ?, ?)""",
                (cotacao_id, item["fornecedor_id"], item["valor_cotado"], item["vencedor"], item["observacoes"]),
            )
        flash("Cotação cadastrada com sucesso.", "success")
        return redirect(url_for("cotacoes.listar"))
    return render_template(
        "cotacoes/form.html", cotacao=None, itens=[], obras=obras, fornecedores=fornecedores,
        categorias=CATEGORIAS, modalidades=MODALIDADES,
    )


@bp.route("/<int:id>/editar", methods=["GET", "POST"])
def editar(id):
    c = query_one("SELECT * FROM cotacoes WHERE id=?", (id,))
    if c is None:
        flash("Cotação não encontrada.", "danger")
        return redirect(url_for("cotacoes.listar"))
    obras = query_all("SELECT * FROM obras ORDER BY descricao")
    fornecedores = query_all("SELECT * FROM fornecedores WHERE ativo=1 ORDER BY nome")
    if request.method == "POST":
        itens = _parse_itens_form()
        if not itens:
            flash("Inclua ao menos um fornecedor para comparar.", "danger")
            return redirect(url_for("cotacoes.editar", id=id))
        execute(
            """UPDATE cotacoes SET obra_id=?, descricao=?, categoria=?, modalidade=?, base_legal=?,
               numero_licitacao=?, valor_estimado=?, data_cotacao=?, observacoes=? WHERE id=?""",
            (
                request.form["obra_id"],
                request.form["descricao"].strip(),
                request.form.get("categoria") or None,
                request.form.get("modalidade") or None,
                request.form.get("base_legal", "").strip(),
                request.form.get("numero_licitacao", "").strip(),
                float(request.form.get("valor_estimado") or 0),
                request.form.get("data_cotacao") or None,
                request.form.get("observacoes", "").strip(),
                id,
            ),
        )
        execute("DELETE FROM cotacoes_itens WHERE cotacao_id=?", (id,), audit=False)
        for item in itens:
            execute(
                """INSERT INTO cotacoes_itens (cotacao_id, fornecedor_id, valor_cotado, vencedor, observacoes)
                   VALUES (?, ?, ?, ?, ?)""",
                (id, item["fornecedor_id"], item["valor_cotado"], item["vencedor"], item["observacoes"]),
            )
        flash("Cotação atualizada com sucesso.", "success")
        return redirect(url_for("cotacoes.listar"))
    return render_template(
        "cotacoes/form.html", cotacao=c, itens=itens_cotacao(id), obras=obras, fornecedores=fornecedores,
        categorias=CATEGORIAS, modalidades=MODALIDADES,
    )


@bp.route("/<int:id>/excluir", methods=["POST"])
def excluir(id):
    execute("DELETE FROM cotacoes WHERE id=?", (id,))
    flash("Cotação excluída.", "success")
    return redirect(url_for("cotacoes.listar"))
