"""
Registro central dos itens de menu do sistema e resolução de permissões
de acesso por usuário.

Administrador sempre tem acesso a tudo — não é configurável, para evitar
que um administrador se tranque fora do próprio sistema por engano.
Para Gestor e Operador, vale a permissão customizada do usuário (se ele
tiver uma configurada em /permissoes) ou, na ausência dela, o padrão do
perfil (o mesmo comportamento que já existia antes deste módulo).

"usuarios" e "permissoes" ficam de fora deste registro de propósito:
continuam restritos a Administrador via @roles_required, e não podem
ser delegados por aqui (evita que alguém conceda a si mesmo o poder de
criar outros administradores).
"""
from db import query_all, execute

MENU_ITEMS = [
    {"chave": "obras", "label": "Obras", "grupo": None},
    {"chave": "relatorios", "label": "Relatórios", "grupo": "Auditoria"},
    {"chave": "mov_consumiveis", "label": "Movimentações (Consumíveis)", "grupo": "Movimentações"},
    {"chave": "mov_patrimonio", "label": "Movimentações (Patrimônio)", "grupo": "Movimentações"},
    {"chave": "entradas", "label": "Entradas de Estoque", "grupo": "Estoque"},
    {"chave": "estoque", "label": "Saldo em Estoque", "grupo": "Estoque"},
    {"chave": "patrimonio", "label": "Bens Patrimoniais", "grupo": "Estoque"},
    {"chave": "solicitacoes_compra", "label": "Solicitações de Compra", "grupo": "Compras"},
    {"chave": "pedidos_compra", "label": "Pedidos de Compra", "grupo": "Compras"},
    {"chave": "licitacoes", "label": "Licitações", "grupo": "Compras"},
    {"chave": "secretarias", "label": "Secretarias", "grupo": "Cadastros"},
    {"chave": "unidades", "label": "Unidades", "grupo": "Cadastros"},
    {"chave": "materiais", "label": "Materiais", "grupo": "Cadastros"},
    {"chave": "fornecedores", "label": "Fornecedores", "grupo": "Cadastros"},
    {"chave": "dashboard", "label": "Dashboard", "grupo": "Auditoria"},
    {"chave": "auditoria", "label": "Log Sistêmico", "grupo": "Auditoria"},
    {"chave": "cotacoes", "label": "Cotação x Projeto", "grupo": None},
]
MENU_CHAVES = {item["chave"] for item in MENU_ITEMS}

# Comportamento padrão de hoje: Operador não acessa Compras/Auditoria.
# Relatórios e Dashboard são liberados para todo mundo por padrão.
_RESTRITO_OPERADOR = {"solicitacoes_compra", "pedidos_compra", "licitacoes", "auditoria"}


def permissoes_padrao(perfil):
    if perfil == "Operador":
        return {c for c in MENU_CHAVES if c not in _RESTRITO_OPERADOR}
    return set(MENU_CHAVES)


def permissoes_customizadas(usuario_id):
    linhas = query_all("SELECT menu_chave FROM usuario_permissoes WHERE usuario_id=?", (usuario_id,))
    return {r["menu_chave"] for r in linhas}


def permissoes_efetivas(user):
    """Conjunto de chaves de menu que este usuário pode acessar agora."""
    if user is None:
        return set()
    if user["perfil"] == "Administrador":
        return set(MENU_CHAVES)
    if user["permissoes_customizadas"]:
        return permissoes_customizadas(user["id"])
    return permissoes_padrao(user["perfil"])


def menu_permitido(user, chave):
    if user is None:
        return False
    if chave not in MENU_CHAVES:
        return True  # rotas fora do registro (ex: auth, home) não são controladas aqui
    return chave in permissoes_efetivas(user)


def salvar_permissoes(usuario_id, chaves_permitidas):
    execute("DELETE FROM usuario_permissoes WHERE usuario_id=?", (usuario_id,), audit=False)
    for chave in chaves_permitidas:
        if chave in MENU_CHAVES:
            execute(
                "INSERT INTO usuario_permissoes (usuario_id, menu_chave) VALUES (?, ?)",
                (usuario_id, chave),
                audit=False,
            )
    execute("UPDATE usuarios SET permissoes_customizadas=1 WHERE id=?", (usuario_id,), audit=False)


def restaurar_padrao(usuario_id):
    execute("DELETE FROM usuario_permissoes WHERE usuario_id=?", (usuario_id,), audit=False)
    execute("UPDATE usuarios SET permissoes_customizadas=0 WHERE id=?", (usuario_id,), audit=False)
