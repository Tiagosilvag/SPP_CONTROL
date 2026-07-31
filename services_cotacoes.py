"""
Regras de negócio do módulo de Cotações: comparação de preços entre
vários fornecedores para uma mesma cotação, com cálculo de economia em
relação ao valor estimado.
"""
from db import query_all, query_one


def listar_cotacoes(obra_id=None, q=None, categoria=None, modalidade=None):
    sql = """SELECT c.*, o.descricao AS obra_descricao, uc.nome AS criado_por_nome,
                    (SELECT ci.valor_cotado FROM cotacoes_itens ci
                       WHERE ci.cotacao_id = c.id AND ci.vencedor = 1 LIMIT 1) AS valor_vencedor,
                    (SELECT f.nome FROM cotacoes_itens ci
                       JOIN fornecedores f ON f.id = ci.fornecedor_id
                       WHERE ci.cotacao_id = c.id AND ci.vencedor = 1 LIMIT 1) AS fornecedor_vencedor,
                    (SELECT COUNT(*) FROM cotacoes_itens ci WHERE ci.cotacao_id = c.id) AS total_fornecedores
             FROM cotacoes c
             JOIN obras o ON o.id = c.obra_id
             LEFT JOIN usuarios uc ON uc.id = c.criado_por
             WHERE 1=1"""
    args = []
    if obra_id:
        sql += " AND c.obra_id=?"
        args.append(obra_id)
    if q:
        sql += " AND c.descricao ILIKE ?"
        args.append(f"%{q}%")
    if categoria:
        sql += " AND c.categoria=?"
        args.append(categoria)
    if modalidade:
        sql += " AND c.modalidade=?"
        args.append(modalidade)
    sql += " ORDER BY c.data_cotacao DESC, c.id DESC"
    rows = query_all(sql, tuple(args))

    linhas = []
    for r in rows:
        valor_estimado = r["valor_estimado"] or 0
        valor_vencedor = r["valor_vencedor"]
        linha = dict(r)
        if valor_vencedor is not None:
            linha["economia"] = valor_estimado - valor_vencedor
            linha["percentual_economia"] = (linha["economia"] / valor_estimado * 100) if valor_estimado else 0
        else:
            linha["economia"] = None
            linha["percentual_economia"] = None
        linhas.append(linha)
    return linhas


def resumo_cotacoes(linhas):
    fechadas = [l for l in linhas if l["valor_vencedor"] is not None]
    total_estimado = sum(l["valor_estimado"] for l in linhas)
    total_vencedor = sum(l["valor_vencedor"] for l in fechadas)
    total_economia = sum(l["economia"] for l in fechadas)
    percentual_geral = (total_economia / total_estimado * 100) if total_estimado else 0
    return {
        "total_registros": len(linhas),
        "total_estimado": total_estimado,
        "total_vencedor": total_vencedor,
        "total_economia": total_economia,
        "percentual_geral": percentual_geral,
    }


def itens_cotacao(cotacao_id):
    return query_all(
        """SELECT ci.*, f.nome AS fornecedor_nome
           FROM cotacoes_itens ci
           JOIN fornecedores f ON f.id = ci.fornecedor_id
           WHERE ci.cotacao_id=?
           ORDER BY ci.valor_cotado""",
        (cotacao_id,),
    )
