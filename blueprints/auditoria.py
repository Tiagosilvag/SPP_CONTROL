from flask import Blueprint, render_template, request
from db import query_all
from auth import roles_required

bp = Blueprint("auditoria", __name__)


@bp.route("/")
@roles_required("Administrador", "Gestor")
def listar():
    usuario_nome = request.args.get("usuario", "").strip()
    tabela = request.args.get("tabela", "")
    operacao = request.args.get("operacao", "")
    data_inicio = request.args.get("data_inicio", "")
    data_fim = request.args.get("data_fim", "")

    sql = "SELECT * FROM auditoria WHERE 1=1"
    args = []
    if usuario_nome:
        sql += " AND usuario_nome ILIKE ?"
        args.append(f"%{usuario_nome}%")
    if tabela:
        sql += " AND tabela=?"
        args.append(tabela)
    if operacao:
        sql += " AND operacao=?"
        args.append(operacao)
    if data_inicio:
        sql += " AND data_hora >= ?"
        args.append(data_inicio)
    if data_fim:
        sql += " AND data_hora < (?::date + INTERVAL '1 day')"
        args.append(data_fim)
    sql += " ORDER BY data_hora DESC LIMIT 500"

    registros = query_all(sql, tuple(args))
    tabelas = [
        r["tabela"]
        for r in query_all("SELECT DISTINCT tabela FROM auditoria ORDER BY tabela")
    ]
    return render_template(
        "auditoria/list.html",
        registros=registros,
        tabelas=tabelas,
        usuario_nome=usuario_nome,
        tabela=tabela,
        operacao=operacao,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )
