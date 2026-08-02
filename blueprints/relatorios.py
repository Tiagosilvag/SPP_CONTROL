from flask import Blueprint, render_template, request, abort
from db import query_all
from export_utils import exportar_excel, exportar_pdf
from services_relatorios import REPORTS, FILTROS_APLICAVEIS

bp = Blueprint("relatorios", __name__)

STATUS_OPTIONS = {
    "secretarias": ["Ativa", "Inativa"],
    "unidades": ["Ativa", "Inativa"],
    "fornecedores": ["Ativo", "Inativo"],
    "patrimonio": ["Disponível", "Em Uso", "Emprestado", "Manutenção", "Baixado"],
    "pedidos": ["Em Elaboração", "Enviado", "Parcialmente Recebido", "Recebido", "Cancelado"],
    "obras": ["Em Andamento", "Concluída", "Cancelada"],
}


def _filtros_da_query():
    return {
        "secretaria_id": request.args.get("secretaria_id", type=int),
        "unidade_id": request.args.get("unidade_id", type=int),
        "obra_id": request.args.get("obra_id", type=int),
        "fornecedor_id": request.args.get("fornecedor_id", type=int),
        "status": request.args.get("status", ""),
        "responsavel": request.args.get("responsavel", "").strip(),
        "data_inicio": request.args.get("data_inicio", ""),
        "data_fim": request.args.get("data_fim", ""),
    }


@bp.route("/")
def listar():
    return render_template("relatorios/list.html", reports=REPORTS)


@bp.route("/<chave>")
def detalhe(chave):
    if chave not in REPORTS:
        abort(404)
    filtros = _filtros_da_query()
    colunas, linhas = REPORTS[chave]["fetch"](filtros)
    return render_template(
        "relatorios/detalhe.html",
        chave=chave,
        report=REPORTS[chave],
        colunas=colunas,
        linhas=linhas[:50],
        total_linhas=len(linhas),
        filtros_aplicaveis=FILTROS_APLICAVEIS.get(chave, []),
        filtros=filtros,
        secretarias=query_all("SELECT * FROM secretarias ORDER BY nome"),
        unidades=query_all("SELECT * FROM unidades ORDER BY nome"),
        obras=query_all("SELECT * FROM obras ORDER BY descricao"),
        fornecedores=query_all("SELECT * FROM fornecedores ORDER BY nome"),
        status_options=STATUS_OPTIONS.get(chave, []),
    )


@bp.route("/<chave>/excel")
def excel(chave):
    if chave not in REPORTS:
        abort(404)
    filtros = _filtros_da_query()
    colunas, linhas = REPORTS[chave]["fetch"](filtros)
    return exportar_excel(REPORTS[chave]["label"], colunas, linhas)


@bp.route("/<chave>/pdf")
def pdf(chave):
    if chave not in REPORTS:
        abort(404)
    filtros = _filtros_da_query()
    colunas, linhas = REPORTS[chave]["fetch"](filtros)
    return exportar_pdf(REPORTS[chave]["label"], colunas, linhas)
