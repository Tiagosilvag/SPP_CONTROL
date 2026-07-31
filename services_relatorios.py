"""
Consultas usadas pelo módulo de Relatórios. Cada relatório expõe as
colunas (chave, rótulo) e busca as linhas já filtradas, para serem
passadas para export_utils.exportar_excel/exportar_pdf.
"""
from db import query_all
from services import calcular_estoque_consumiveis

FILTROS_APLICAVEIS = {
    "estoque": ["secretaria_id"],
    "entradas": ["secretaria_id", "unidade_id", "obra_id", "fornecedor_id", "data_inicio", "data_fim"],
    "saidas": ["secretaria_id", "obra_id", "data_inicio", "data_fim"],
    "patrimonio": ["secretaria_id", "unidade_id", "status"],
    "pedidos": ["secretaria_id", "unidade_id", "fornecedor_id", "status", "responsavel", "data_inicio", "data_fim"],
    "compras": ["fornecedor_id", "data_inicio", "data_fim"],
    "fornecedores": ["status"],
    "licitacoes": ["status"],
    "auditoria": ["responsavel", "data_inicio", "data_fim"],
    "movimentacoes": ["unidade_id", "obra_id", "responsavel", "data_inicio", "data_fim"],
    "obras": ["secretaria_id", "unidade_id", "status"],
    "secretarias": ["status"],
    "unidades": ["secretaria_id", "status"],
}


def _f(filtros, chave):
    return filtros.get(chave) or None


def relatorio_estoque(filtros):
    colunas = [
        ("material_nome", "Material"), ("secretaria_sigla", "Secretaria"),
        ("estoque_disponivel", "Saldo Disponível"), ("estoque_minimo", "Estoque Mínimo"),
        ("status_alerta", "Status"),
    ]
    linhas = calcular_estoque_consumiveis()
    secretaria_id = _f(filtros, "secretaria_id")
    if secretaria_id:
        linhas = [l for l in linhas if l["secretaria_id"] == int(secretaria_id)]
    return colunas, linhas


def relatorio_entradas(filtros):
    colunas = [
        ("data_entrada", "Data"), ("material_nome", "Material"), ("quantidade", "Quantidade"),
        ("secretaria_sigla", "Secretaria"), ("unidade_nome", "Unidade"), ("fornecedor_nome", "Fornecedor"),
        ("nota_fiscal", "Nota Fiscal"), ("obra_descricao", "Obra"),
    ]
    sql = """SELECT e.data_entrada, m.nome AS material_nome, e.quantidade, s.sigla AS secretaria_sigla,
                    u.nome AS unidade_nome, f.nome AS fornecedor_nome, e.nota_fiscal, o.descricao AS obra_descricao
             FROM entradas_estoque e
             JOIN materiais m ON m.id = e.material_id
             LEFT JOIN secretarias s ON s.id = e.secretaria_proprietaria_id
             LEFT JOIN unidades u ON u.id = e.unidade_destino_id
             LEFT JOIN fornecedores f ON f.id = e.fornecedor_id
             LEFT JOIN obras o ON o.id = e.obra_id
             WHERE 1=1"""
    args = []
    if _f(filtros, "secretaria_id"):
        sql += " AND e.secretaria_proprietaria_id=?"; args.append(filtros["secretaria_id"])
    if _f(filtros, "unidade_id"):
        sql += " AND e.unidade_destino_id=?"; args.append(filtros["unidade_id"])
    if _f(filtros, "obra_id"):
        sql += " AND e.obra_id=?"; args.append(filtros["obra_id"])
    if _f(filtros, "fornecedor_id"):
        sql += " AND e.fornecedor_id=?"; args.append(filtros["fornecedor_id"])
    if _f(filtros, "data_inicio"):
        sql += " AND e.data_entrada::date >= ?::date"; args.append(filtros["data_inicio"])
    if _f(filtros, "data_fim"):
        sql += " AND e.data_entrada::date <= ?::date"; args.append(filtros["data_fim"])
    sql += " ORDER BY e.data_entrada DESC"
    return colunas, query_all(sql, tuple(args))


def relatorio_saidas(filtros):
    colunas = [
        ("data_movimentacao", "Data"), ("material_nome", "Material"), ("quantidade", "Quantidade"),
        ("secretaria_sigla", "Secretaria"), ("obra_descricao", "Obra"), ("responsavel", "Responsável"),
    ]
    sql = """SELECT mc.data_movimentacao, m.nome AS material_nome, mc.quantidade,
                    s.sigla AS secretaria_sigla, o.descricao AS obra_descricao, mc.responsavel
             FROM movimentacoes_consumiveis mc
             JOIN materiais m ON m.id = mc.material_id
             LEFT JOIN secretarias s ON s.id = mc.secretaria_proprietaria_id
             LEFT JOIN obras o ON o.id = mc.obra_id
             WHERE mc.tipo_movimentacao = 'Consumo em Obra'"""
    args = []
    if _f(filtros, "secretaria_id"):
        sql += " AND mc.secretaria_proprietaria_id=?"; args.append(filtros["secretaria_id"])
    if _f(filtros, "obra_id"):
        sql += " AND mc.obra_id=?"; args.append(filtros["obra_id"])
    if _f(filtros, "data_inicio"):
        sql += " AND mc.data_movimentacao::date >= ?::date"; args.append(filtros["data_inicio"])
    if _f(filtros, "data_fim"):
        sql += " AND mc.data_movimentacao::date <= ?::date"; args.append(filtros["data_fim"])
    sql += " ORDER BY mc.data_movimentacao DESC"
    return colunas, query_all(sql, tuple(args))


def relatorio_patrimonio(filtros):
    colunas = [
        ("num_patrimonio", "Nº Patrimônio"), ("material_nome", "Material"), ("secretaria_sigla", "Secretaria"),
        ("unidade_nome", "Unidade Atual"), ("estado_conservacao", "Estado"), ("status", "Status"),
    ]
    sql = """SELECT p.num_patrimonio, m.nome AS material_nome, s.sigla AS secretaria_sigla,
                    u.nome AS unidade_nome, p.estado_conservacao, p.status
             FROM patrimonios p
             JOIN materiais m ON m.id = p.material_id
             LEFT JOIN secretarias s ON s.id = p.secretaria_proprietaria_id
             LEFT JOIN unidades u ON u.id = p.unidade_atual_id
             WHERE 1=1"""
    args = []
    if _f(filtros, "secretaria_id"):
        sql += " AND p.secretaria_proprietaria_id=?"; args.append(filtros["secretaria_id"])
    if _f(filtros, "unidade_id"):
        sql += " AND p.unidade_atual_id=?"; args.append(filtros["unidade_id"])
    if _f(filtros, "status"):
        sql += " AND p.status=?"; args.append(filtros["status"])
    sql += " ORDER BY p.num_patrimonio"
    return colunas, query_all(sql, tuple(args))


def relatorio_pedidos(filtros):
    colunas = [
        ("numero_pedido", "Número"), ("data_pedido", "Data"), ("secretaria_sigla", "Secretaria"),
        ("unidade_nome", "Unidade"), ("fornecedor_nome", "Fornecedor"), ("responsavel", "Responsável"),
        ("status", "Status"),
    ]
    sql = """SELECT p.numero_pedido, p.data_pedido, s.sigla AS secretaria_sigla, u.nome AS unidade_nome,
                    f.nome AS fornecedor_nome, p.responsavel, p.status
             FROM pedidos_compra p
             LEFT JOIN secretarias s ON s.id = p.secretaria_id
             LEFT JOIN unidades u ON u.id = p.unidade_id
             LEFT JOIN fornecedores f ON f.id = p.fornecedor_id
             WHERE 1=1"""
    args = []
    if _f(filtros, "secretaria_id"):
        sql += " AND p.secretaria_id=?"; args.append(filtros["secretaria_id"])
    if _f(filtros, "unidade_id"):
        sql += " AND p.unidade_id=?"; args.append(filtros["unidade_id"])
    if _f(filtros, "fornecedor_id"):
        sql += " AND p.fornecedor_id=?"; args.append(filtros["fornecedor_id"])
    if _f(filtros, "status"):
        sql += " AND p.status=?"; args.append(filtros["status"])
    if _f(filtros, "responsavel"):
        sql += " AND p.responsavel ILIKE ?"; args.append(f"%{filtros['responsavel']}%")
    if _f(filtros, "data_inicio"):
        sql += " AND p.data_pedido >= ?"; args.append(filtros["data_inicio"])
    if _f(filtros, "data_fim"):
        sql += " AND p.data_pedido <= ?"; args.append(filtros["data_fim"])
    sql += " ORDER BY p.id DESC"
    return colunas, query_all(sql, tuple(args))


def relatorio_compras(filtros):
    colunas = [
        ("numero_pedido", "Pedido"), ("data_pedido", "Data"), ("fornecedor_nome", "Fornecedor"),
        ("material_nome", "Material"), ("quantidade_solicitada", "Qtd. Solicitada"),
        ("valor_unitario", "Valor Unit."), ("valor_total", "Valor Total"),
    ]
    sql = """SELECT p.numero_pedido, p.data_pedido, f.nome AS fornecedor_nome, m.nome AS material_nome,
                    pi.quantidade_solicitada, pi.valor_unitario,
                    (pi.quantidade_solicitada * pi.valor_unitario) AS valor_total
             FROM pedidos_compra_itens pi
             JOIN pedidos_compra p ON p.id = pi.pedido_id
             JOIN materiais m ON m.id = pi.material_id
             LEFT JOIN fornecedores f ON f.id = p.fornecedor_id
             WHERE 1=1"""
    args = []
    if _f(filtros, "fornecedor_id"):
        sql += " AND p.fornecedor_id=?"; args.append(filtros["fornecedor_id"])
    if _f(filtros, "data_inicio"):
        sql += " AND p.data_pedido >= ?"; args.append(filtros["data_inicio"])
    if _f(filtros, "data_fim"):
        sql += " AND p.data_pedido <= ?"; args.append(filtros["data_fim"])
    sql += " ORDER BY p.id DESC"
    return colunas, query_all(sql, tuple(args))


def relatorio_fornecedores(filtros):
    colunas = [("nome", "Nome"), ("cnpj", "CNPJ"), ("contato", "Contato"), ("ativo", "Ativo")]
    sql = "SELECT nome, cnpj, contato, ativo FROM fornecedores WHERE 1=1"
    args = []
    if _f(filtros, "status"):
        sql += " AND ativo=?"; args.append(1 if filtros["status"] == "Ativo" else 0)
    sql += " ORDER BY nome"
    return colunas, query_all(sql, tuple(args))


def relatorio_licitacoes(filtros):
    colunas = [
        ("processo", "Processo"), ("objeto", "Objeto"), ("categoria", "Categoria"),
        ("modalidade", "Modalidade"), ("valor_estimado", "Valor Estimado"), ("valor_homologado", "Valor Homologado"),
    ]
    return colunas, query_all("SELECT * FROM licitacoes ORDER BY id DESC")


def relatorio_auditoria(filtros):
    colunas = [
        ("data_hora", "Data/Hora"), ("usuario_nome", "Usuário"), ("operacao", "Operação"),
        ("tabela", "Tabela"), ("registro_id", "Registro"),
    ]
    sql = "SELECT data_hora, usuario_nome, operacao, tabela, registro_id FROM auditoria WHERE 1=1"
    args = []
    if _f(filtros, "responsavel"):
        sql += " AND usuario_nome ILIKE ?"; args.append(f"%{filtros['responsavel']}%")
    if _f(filtros, "data_inicio"):
        sql += " AND data_hora >= ?"; args.append(filtros["data_inicio"])
    if _f(filtros, "data_fim"):
        sql += " AND data_hora < (?::date + INTERVAL '1 day')"; args.append(filtros["data_fim"])
    sql += " ORDER BY data_hora DESC LIMIT 1000"
    return colunas, query_all(sql, tuple(args))


def relatorio_movimentacoes(filtros):
    colunas = [
        ("data_movimentacao", "Data"), ("tipo_movimentacao", "Tipo"), ("num_patrimonio", "Patrimônio"),
        ("unidade_origem_nome", "Origem"), ("unidade_destino_nome", "Destino"), ("obra_descricao", "Obra"),
        ("responsavel", "Responsável"),
    ]
    sql = """SELECT mp.data_movimentacao, mp.tipo_movimentacao, p.num_patrimonio,
                    uo.nome AS unidade_origem_nome, ud.nome AS unidade_destino_nome,
                    o.descricao AS obra_descricao, mp.responsavel
             FROM movimentacoes_patrimonio mp
             JOIN patrimonios p ON p.id = mp.patrimonio_id
             LEFT JOIN unidades uo ON uo.id = mp.unidade_origem_id
             LEFT JOIN unidades ud ON ud.id = mp.unidade_destino_id
             LEFT JOIN obras o ON o.id = mp.obra_id
             WHERE 1=1"""
    args = []
    if _f(filtros, "unidade_id"):
        sql += " AND (mp.unidade_origem_id=? OR mp.unidade_destino_id=?)"; args.extend([filtros["unidade_id"], filtros["unidade_id"]])
    if _f(filtros, "obra_id"):
        sql += " AND mp.obra_id=?"; args.append(filtros["obra_id"])
    if _f(filtros, "responsavel"):
        sql += " AND mp.responsavel ILIKE ?"; args.append(f"%{filtros['responsavel']}%")
    if _f(filtros, "data_inicio"):
        sql += " AND mp.data_movimentacao::date >= ?::date"; args.append(filtros["data_inicio"])
    if _f(filtros, "data_fim"):
        sql += " AND mp.data_movimentacao::date <= ?::date"; args.append(filtros["data_fim"])
    sql += " ORDER BY mp.data_movimentacao DESC"
    return colunas, query_all(sql, tuple(args))


def relatorio_obras(filtros):
    colunas = [
        ("descricao", "Descrição"), ("secretaria_sigla", "Secretaria"), ("unidade_nome", "Unidade"),
        ("data_inicio", "Início"), ("previsao_termino", "Previsão Término"), ("status", "Status"),
    ]
    sql = """SELECT o.descricao, s.sigla AS secretaria_sigla, u.nome AS unidade_nome,
                    o.data_inicio, o.previsao_termino, o.status
             FROM obras o
             LEFT JOIN secretarias s ON s.id = o.secretaria_solicitante_id
             LEFT JOIN unidades u ON u.id = o.unidade_local_id
             WHERE 1=1"""
    args = []
    if _f(filtros, "secretaria_id"):
        sql += " AND o.secretaria_solicitante_id=?"; args.append(filtros["secretaria_id"])
    if _f(filtros, "unidade_id"):
        sql += " AND o.unidade_local_id=?"; args.append(filtros["unidade_id"])
    if _f(filtros, "status"):
        sql += " AND o.status=?"; args.append(filtros["status"])
    sql += " ORDER BY o.data_inicio DESC"
    return colunas, query_all(sql, tuple(args))


def relatorio_secretarias(filtros):
    colunas = [("nome", "Nome"), ("sigla", "Sigla"), ("responsavel", "Responsável"), ("ativa", "Ativa")]
    sql = "SELECT nome, sigla, responsavel, ativa FROM secretarias WHERE 1=1"
    args = []
    if _f(filtros, "status"):
        sql += " AND ativa=?"; args.append(1 if filtros["status"] == "Ativa" else 0)
    sql += " ORDER BY nome"
    return colunas, query_all(sql, tuple(args))


def relatorio_unidades(filtros):
    colunas = [("nome", "Nome"), ("secretaria_sigla", "Secretaria"), ("endereco", "Endereço"), ("ativa", "Ativa")]
    sql = """SELECT u.nome, s.sigla AS secretaria_sigla, u.endereco, u.ativa
             FROM unidades u LEFT JOIN secretarias s ON s.id = u.secretaria_id WHERE 1=1"""
    args = []
    if _f(filtros, "secretaria_id"):
        sql += " AND u.secretaria_id=?"; args.append(filtros["secretaria_id"])
    if _f(filtros, "status"):
        sql += " AND u.ativa=?"; args.append(1 if filtros["status"] == "Ativa" else 0)
    sql += " ORDER BY u.nome"
    return colunas, query_all(sql, tuple(args))


REPORTS = {
    "estoque": {"label": "Saldo em Estoque", "icon": "bi-clipboard-data", "fetch": relatorio_estoque},
    "entradas": {"label": "Entradas de Estoque", "icon": "bi-box-arrow-in-down", "fetch": relatorio_entradas},
    "saidas": {"label": "Saídas (Consumo em Obra)", "icon": "bi-box-arrow-up", "fetch": relatorio_saidas},
    "patrimonio": {"label": "Patrimônio", "icon": "bi-tools", "fetch": relatorio_patrimonio},
    "pedidos": {"label": "Pedidos de Compra", "icon": "bi-cart4", "fetch": relatorio_pedidos},
    "compras": {"label": "Compras (itens)", "icon": "bi-bag-check", "fetch": relatorio_compras},
    "fornecedores": {"label": "Fornecedores", "icon": "bi-truck", "fetch": relatorio_fornecedores},
    "licitacoes": {"label": "Licitações", "icon": "bi-file-earmark-text", "fetch": relatorio_licitacoes},
    "auditoria": {"label": "Auditoria", "icon": "bi-journal-text", "fetch": relatorio_auditoria},
    "movimentacoes": {"label": "Movimentações de Patrimônio", "icon": "bi-arrow-repeat", "fetch": relatorio_movimentacoes},
    "obras": {"label": "Obras", "icon": "bi-cone-striped", "fetch": relatorio_obras},
    "secretarias": {"label": "Secretarias", "icon": "bi-building", "fetch": relatorio_secretarias},
    "unidades": {"label": "Unidades", "icon": "bi-geo-alt", "fetch": relatorio_unidades},
}
