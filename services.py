"""
Regras de negócio do SPP - Control.

Este módulo concentra a lógica que, na planilha original, era feita por
fórmulas (aba "Estoque_Consumiveis") e por atualização manual de status
(aba "Patrimônio"). Aqui isso é recalculado dinamicamente a partir do
histórico de Entradas e Movimentações, evitando divergência de dados.
"""
from datetime import date
from db import query_all, query_one, execute

TIPOS_MOV_CONSUMIVEL = ["Consumo em Obra", "Transferência", "Transferência entre Obras", "Retorno", "Devolução", "Empréstimo"]
TIPOS_MOV_PATRIMONIO = ["Transferência", "Transferência entre Obras", "Devolução", "Empréstimo", "Retorno", "Manutenção"]

# Botões de ação rápida nas telas de movimentação (item 10). Empréstimo de
# consumíveis é incomum na prática — fica disponível no formulário, mas
# fora dos atalhos, conforme pedido.
QUICK_TIPOS_CONSUMIVEL = ["Transferência", "Transferência entre Obras", "Retorno", "Devolução"]
QUICK_TIPOS_PATRIMONIO = ["Transferência", "Devolução", "Empréstimo", "Retorno", "Manutenção"]


def calcular_estoque_consumiveis():
    """Recalcula o estoque de todos os materiais consumíveis, por secretaria
    proprietária, replicando (e substituindo) a aba Estoque_Consumiveis."""

    pares = query_all(
        """
        SELECT DISTINCT m.id AS material_id, m.nome AS material_nome, m.categoria,
               m.unidade_medida, m.estoque_minimo,
               e.secretaria_proprietaria_id AS secretaria_id, s.sigla AS secretaria_sigla,
               s.nome AS secretaria_nome
        FROM entradas_estoque e
        JOIN materiais m ON m.id = e.material_id
        LEFT JOIN secretarias s ON s.id = e.secretaria_proprietaria_id
        WHERE m.tipo_material = 'Consumível'
        """
    )

    linhas = []
    for row in pares:
        material_id = row["material_id"]
        sec_id = row["secretaria_id"]

        total_entradas = query_one(
            """SELECT COALESCE(SUM(quantidade),0) AS total FROM entradas_estoque
               WHERE material_id=? AND secretaria_proprietaria_id=?""",
            (material_id, sec_id),
        )["total"]

        total_consumido = query_one(
            """SELECT COALESCE(SUM(quantidade),0) AS total FROM movimentacoes_consumiveis
               WHERE material_id=? AND secretaria_proprietaria_id=? AND tipo_movimentacao='Consumo em Obra'""",
            (material_id, sec_id),
        )["total"]

        total_emprestado_saida = query_one(
            """SELECT COALESCE(SUM(quantidade),0) AS total FROM movimentacoes_consumiveis
               WHERE material_id=? AND secretaria_proprietaria_id=? AND tipo_movimentacao='Empréstimo'""",
            (material_id, sec_id),
        )["total"]

        total_devolvido = query_one(
            """SELECT COALESCE(SUM(quantidade),0) AS total FROM movimentacoes_consumiveis
               WHERE material_id=? AND secretaria_proprietaria_id=? AND tipo_movimentacao='Devolução'""",
            (material_id, sec_id),
        )["total"]

        total_emprestado = max(total_emprestado_saida - total_devolvido, 0)
        estoque_disponivel = total_entradas - total_consumido - total_emprestado
        estoque_minimo = row["estoque_minimo"] or 0

        if estoque_disponivel <= estoque_minimo:
            status_alerta = "Crítico"
        elif estoque_disponivel <= estoque_minimo * 1.5:
            status_alerta = "Atenção"
        else:
            status_alerta = "OK"

        linhas.append(
            {
                "material_id": material_id,
                "material_nome": row["material_nome"],
                "categoria": row["categoria"],
                "unidade_medida": row["unidade_medida"],
                "secretaria_id": sec_id,
                "secretaria_sigla": row["secretaria_sigla"],
                "secretaria_nome": row["secretaria_nome"],
                "total_entradas": total_entradas,
                "total_consumido": total_consumido,
                "total_emprestado": total_emprestado,
                "estoque_disponivel": estoque_disponivel,
                "estoque_minimo": estoque_minimo,
                "status_alerta": status_alerta,
            }
        )

    linhas.sort(key=lambda l: (l["material_nome"], l["secretaria_nome"] or ""))
    return linhas


def saldo_material_secretaria(material_id, secretaria_id):
    """Retorna o saldo disponível de um material específico para uma secretaria."""
    for linha in calcular_estoque_consumiveis():
        if linha["material_id"] == material_id and linha["secretaria_id"] == secretaria_id:
            return linha["estoque_disponivel"]
    return 0


def aplicar_efeito_movimentacao_patrimonio(mov_id):
    """Atualiza o status/localização atual do item de patrimônio conforme o
    tipo de movimentação registrada (equivalente ao que era feito manualmente
    na aba Patrimônio da planilha)."""

    mov = query_one("SELECT * FROM movimentacoes_patrimonio WHERE id=?", (mov_id,))
    if mov is None:
        return
    patrimonio_id = mov["patrimonio_id"]
    tipo = mov["tipo_movimentacao"]

    if tipo == "Empréstimo":
        novo_status = "Emprestado"
        unidade_atual = mov["unidade_destino_id"]
        execute(
            "UPDATE patrimonios SET status=?, unidade_atual_id=COALESCE(?, unidade_atual_id) WHERE id=?",
            (novo_status, unidade_atual, patrimonio_id),
        )
        if mov["status_devolucao"] in (None, "—"):
            execute(
                "UPDATE movimentacoes_patrimonio SET status_devolucao='Pendente' WHERE id=?",
                (mov_id,),
            )

    elif tipo in ("Transferência", "Transferência entre Obras"):
        execute(
            "UPDATE patrimonios SET status='Em Uso', unidade_atual_id=COALESCE(?, unidade_atual_id) WHERE id=?",
            (mov["unidade_destino_id"], patrimonio_id),
        )

    elif tipo == "Manutenção":
        execute("UPDATE patrimonios SET status='Manutenção' WHERE id=?", (patrimonio_id,))

    elif tipo == "Retorno":
        destino = mov["unidade_destino_id"] or mov["unidade_origem_id"]
        execute(
            "UPDATE patrimonios SET status='Disponível', unidade_atual_id=COALESCE(?, unidade_atual_id) WHERE id=?",
            (destino, patrimonio_id),
        )

    elif tipo == "Devolução":
        destino = mov["unidade_destino_id"] or mov["unidade_origem_id"]
        execute(
            "UPDATE patrimonios SET status='Disponível', unidade_atual_id=COALESCE(?, unidade_atual_id) WHERE id=?",
            (destino, patrimonio_id),
        )
        hoje = mov["data_real_devolucao"] or date.today().isoformat()
        execute(
            "UPDATE movimentacoes_patrimonio SET status_devolucao='Devolvido', data_real_devolucao=? WHERE id=?",
            (hoje, mov_id),
        )

        # Marca o empréstimo pendente mais recente deste bem como devolvido
        emprestimo_pendente = query_one(
            """SELECT id FROM movimentacoes_patrimonio
               WHERE patrimonio_id=? AND tipo_movimentacao='Empréstimo' AND status_devolucao != 'Devolvido'
               ORDER BY data_movimentacao DESC LIMIT 1""",
            (patrimonio_id,),
        )
        if emprestimo_pendente:
            execute(
                "UPDATE movimentacoes_patrimonio SET status_devolucao='Devolvido', data_real_devolucao=? WHERE id=?",
                (hoje, emprestimo_pendente["id"]),
            )


def dashboard_stats():
    """Reúne indicadores gerais para a tela inicial do sistema."""
    total_secretarias = query_one("SELECT COUNT(*) AS c FROM secretarias WHERE ativa=1")["c"]
    total_materiais = query_one("SELECT COUNT(*) AS c FROM materiais WHERE ativo=1")["c"]
    total_patrimonios = query_one("SELECT COUNT(*) AS c FROM patrimonios")["c"]

    estoque = calcular_estoque_consumiveis()
    criticos = [l for l in estoque if l["status_alerta"] == "Crítico"]
    atencao = [l for l in estoque if l["status_alerta"] == "Atenção"]

    emprestimos_atraso = query_one(
        "SELECT COUNT(*) AS c FROM movimentacoes_patrimonio WHERE status_devolucao='Em Atraso'"
    )["c"]
    emprestimos_pendentes = query_one(
        "SELECT COUNT(*) AS c FROM movimentacoes_patrimonio WHERE status_devolucao='Pendente'"
    )["c"]

    patrimonio_por_status = {
        r["status"]: r["c"]
        for r in query_all("SELECT status, COUNT(*) AS c FROM patrimonios GROUP BY status")
    }

    compras_pendentes = query_one(
        "SELECT COUNT(*) AS c FROM pedidos_compra WHERE status IN ('Enviado', 'Parcialmente Recebido')"
    )["c"]
    entregas_parciais = query_one(
        "SELECT COUNT(*) AS c FROM pedidos_compra WHERE status = 'Parcialmente Recebido'"
    )["c"]
    patrimonios_emprestados = patrimonio_por_status.get("Emprestado", 0)
    patrimonios_manutencao = patrimonio_por_status.get("Manutenção", 0)

    return {
        "total_secretarias": total_secretarias,
        "total_materiais": total_materiais,
        "total_patrimonios": total_patrimonios,
        "itens_criticos": len(criticos),
        "itens_atencao": len(atencao),
        "criticos": criticos[:8],
        "emprestimos_atraso": emprestimos_atraso,
        "emprestimos_pendentes": emprestimos_pendentes,
        "patrimonio_por_status": patrimonio_por_status,
        "compras_pendentes": compras_pendentes,
        "entregas_parciais": entregas_parciais,
        "patrimonios_emprestados": patrimonios_emprestados,
        "patrimonios_manutencao": patrimonios_manutencao,
    }
