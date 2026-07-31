CREATE TABLE IF NOT EXISTS secretarias (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL,
    sigla TEXT NOT NULL,
    responsavel TEXT,
    contato TEXT,
    ativa INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS unidades (
    id SERIAL PRIMARY KEY,
    secretaria_id INTEGER NOT NULL REFERENCES secretarias(id),
    nome TEXT NOT NULL,
    endereco TEXT,
    responsavel_local TEXT,
    ativa INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS materiais (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL,
    tipo_material TEXT NOT NULL,      -- 'Consumível' ou 'Patrimonial'
    categoria TEXT,
    unidade_medida TEXT,
    estoque_minimo DOUBLE PRECISION DEFAULT 0,
    ativo INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS fornecedores (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL,
    cnpj TEXT,
    contato TEXT,
    ativo INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS obras (
    id SERIAL PRIMARY KEY,
    descricao TEXT NOT NULL,
    secretaria_solicitante_id INTEGER REFERENCES secretarias(id),
    unidade_local_id INTEGER REFERENCES unidades(id),
    data_inicio TEXT,
    previsao_termino TEXT,
    status TEXT DEFAULT 'Em Andamento',
    fiscal_responsavel TEXT,
    observacoes TEXT
);

CREATE TABLE IF NOT EXISTS patrimonios (
    id SERIAL PRIMARY KEY,
    num_patrimonio TEXT UNIQUE NOT NULL,
    material_id INTEGER NOT NULL REFERENCES materiais(id),
    secretaria_proprietaria_id INTEGER REFERENCES secretarias(id),
    data_aquisicao TEXT,
    estado_conservacao TEXT DEFAULT 'Bom',
    unidade_atual_id INTEGER REFERENCES unidades(id),
    status TEXT DEFAULT 'Disponível',
    observacoes TEXT
);

CREATE TABLE IF NOT EXISTS entradas_estoque (
    id SERIAL PRIMARY KEY,
    data_entrada TEXT NOT NULL,
    material_id INTEGER NOT NULL REFERENCES materiais(id),
    secretaria_proprietaria_id INTEGER REFERENCES secretarias(id),
    unidade_destino_id INTEGER REFERENCES unidades(id),
    fornecedor_id INTEGER REFERENCES fornecedores(id),
    quantidade DOUBLE PRECISION NOT NULL,
    nota_fiscal TEXT,
    obra_id INTEGER REFERENCES obras(id),
    observacoes TEXT
);

CREATE TABLE IF NOT EXISTS movimentacoes_consumiveis (
    id SERIAL PRIMARY KEY,
    data_movimentacao TEXT NOT NULL,
    tipo_movimentacao TEXT NOT NULL,
    material_id INTEGER NOT NULL REFERENCES materiais(id),
    quantidade DOUBLE PRECISION NOT NULL,
    unidade_origem_id INTEGER REFERENCES unidades(id),
    unidade_destino_id INTEGER REFERENCES unidades(id),
    secretaria_proprietaria_id INTEGER REFERENCES secretarias(id),
    obra_id INTEGER REFERENCES obras(id),
    data_prev_devolucao TEXT,
    data_real_devolucao TEXT,
    status_devolucao TEXT DEFAULT '—',
    responsavel TEXT,
    observacoes TEXT
);

CREATE TABLE IF NOT EXISTS movimentacoes_patrimonio (
    id SERIAL PRIMARY KEY,
    data_movimentacao TEXT NOT NULL,
    tipo_movimentacao TEXT NOT NULL,
    patrimonio_id INTEGER NOT NULL REFERENCES patrimonios(id),
    secretaria_proprietaria_id INTEGER REFERENCES secretarias(id),
    unidade_origem_id INTEGER REFERENCES unidades(id),
    unidade_destino_id INTEGER REFERENCES unidades(id),
    obra_id INTEGER REFERENCES obras(id),
    data_prev_devolucao TEXT,
    data_real_devolucao TEXT,
    status_devolucao TEXT DEFAULT '—',
    responsavel TEXT,
    observacoes TEXT
);

-- Cotações: cabeçalho. Reestruturada para comparar vários fornecedores
-- (ver cotacoes_itens). Tabela estava vazia em produção, então as colunas
-- antigas (fornecedor_id, valor_cotado, valor_economizado) foram removidas
-- sem risco de perda de dado.
CREATE TABLE IF NOT EXISTS cotacoes (
    id SERIAL PRIMARY KEY,
    obra_id INTEGER NOT NULL REFERENCES obras(id),
    descricao TEXT NOT NULL,
    data_cotacao TEXT,
    observacoes TEXT
);
ALTER TABLE cotacoes DROP COLUMN IF EXISTS fornecedor_id;
ALTER TABLE cotacoes DROP COLUMN IF EXISTS valor_cotado;
ALTER TABLE cotacoes DROP COLUMN IF EXISTS valor_economizado;
ALTER TABLE cotacoes ADD COLUMN IF NOT EXISTS categoria TEXT;
ALTER TABLE cotacoes ADD COLUMN IF NOT EXISTS modalidade TEXT;
ALTER TABLE cotacoes ADD COLUMN IF NOT EXISTS base_legal TEXT;
ALTER TABLE cotacoes ADD COLUMN IF NOT EXISTS numero_licitacao TEXT;
ALTER TABLE cotacoes ADD COLUMN IF NOT EXISTS valor_estimado DOUBLE PRECISION NOT NULL DEFAULT 0;
ALTER TABLE cotacoes ADD COLUMN IF NOT EXISTS criado_por INTEGER;
ALTER TABLE cotacoes ADD COLUMN IF NOT EXISTS criado_em TIMESTAMP NOT NULL DEFAULT now();

-- Um item por fornecedor comparado dentro de uma cotação.
CREATE TABLE IF NOT EXISTS cotacoes_itens (
    id SERIAL PRIMARY KEY,
    cotacao_id INTEGER NOT NULL REFERENCES cotacoes(id) ON DELETE CASCADE,
    fornecedor_id INTEGER NOT NULL REFERENCES fornecedores(id),
    valor_cotado DOUBLE PRECISION NOT NULL,
    vencedor INTEGER NOT NULL DEFAULT 0,
    observacoes TEXT
);

-- Usuários: já existia (cadastro reservado). Ganha campos de autenticação
-- e trilha de criação/acesso para o módulo de Login (item 5).
CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    senha_hash TEXT NOT NULL,
    perfil TEXT DEFAULT 'Operador',   -- 'Administrador', 'Gestor' ou 'Operador'
    ativo INTEGER NOT NULL DEFAULT 1
);
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS ultimo_acesso TIMESTAMP;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS criado_em TIMESTAMP NOT NULL DEFAULT now();
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS criado_por INTEGER REFERENCES usuarios(id);

-- Auditoria (item 6): uma linha por operação de escrita (INSERT/UPDATE/DELETE)
-- feita através da aplicação. Populada automaticamente por db.py.
CREATE TABLE IF NOT EXISTS auditoria (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER REFERENCES usuarios(id),
    usuario_nome TEXT,
    data_hora TIMESTAMP NOT NULL DEFAULT now(),
    ip TEXT,
    operacao TEXT NOT NULL,   -- INSERT, UPDATE, DELETE
    tabela TEXT NOT NULL,
    registro_id INTEGER,
    valor_anterior TEXT,      -- JSON
    valor_novo TEXT           -- JSON
);

-- Pedidos de Compra (item 1): cabeçalho.
CREATE TABLE IF NOT EXISTS pedidos_compra (
    id SERIAL PRIMARY KEY,
    numero_pedido TEXT UNIQUE NOT NULL,
    data_pedido TEXT NOT NULL,
    secretaria_id INTEGER REFERENCES secretarias(id),
    unidade_id INTEGER REFERENCES unidades(id),
    fornecedor_id INTEGER REFERENCES fornecedores(id),
    responsavel TEXT,
    status TEXT NOT NULL DEFAULT 'Em Elaboração',
    previsao_entrega TEXT,
    observacoes TEXT,
    criado_por INTEGER REFERENCES usuarios(id),
    criado_em TIMESTAMP NOT NULL DEFAULT now()
);

-- Itens do pedido. quantidade_pendente é sempre calculada
-- (quantidade_solicitada - quantidade_atendida), nunca armazenada, para
-- não correr o risco de ficar dessincronizada.
CREATE TABLE IF NOT EXISTS pedidos_compra_itens (
    id SERIAL PRIMARY KEY,
    pedido_id INTEGER NOT NULL REFERENCES pedidos_compra(id) ON DELETE CASCADE,
    material_id INTEGER NOT NULL REFERENCES materiais(id),
    quantidade_solicitada DOUBLE PRECISION NOT NULL,
    quantidade_atendida DOUBLE PRECISION NOT NULL DEFAULT 0,
    valor_unitario DOUBLE PRECISION NOT NULL DEFAULT 0,
    observacoes TEXT
);

-- Recebimento parcial (item 2): cada recebimento é um evento de entrega
-- do fornecedor; um pedido pode ter vários. Cada recebimento_itens dá
-- baixa em pedidos_compra_itens.quantidade_atendida.
CREATE TABLE IF NOT EXISTS recebimentos (
    id SERIAL PRIMARY KEY,
    pedido_id INTEGER NOT NULL REFERENCES pedidos_compra(id),
    data_recebimento TEXT NOT NULL,
    nota_fiscal TEXT,
    responsavel TEXT,
    observacoes TEXT,
    criado_por INTEGER REFERENCES usuarios(id),
    criado_em TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS recebimento_itens (
    id SERIAL PRIMARY KEY,
    recebimento_id INTEGER NOT NULL REFERENCES recebimentos(id) ON DELETE CASCADE,
    pedido_item_id INTEGER NOT NULL REFERENCES pedidos_compra_itens(id),
    quantidade_recebida DOUBLE PRECISION NOT NULL
);

-- Licitações (item 8).
CREATE TABLE IF NOT EXISTS licitacoes (
    id SERIAL PRIMARY KEY,
    categoria TEXT,
    modalidade TEXT,
    objeto TEXT NOT NULL,
    processo TEXT,
    valor_estimado DOUBLE PRECISION DEFAULT 0,
    valor_homologado DOUBLE PRECISION,
    observacoes TEXT,
    criado_por INTEGER REFERENCES usuarios(id),
    criado_em TIMESTAMP NOT NULL DEFAULT now()
);

-- Entradas de estoque: link opcional a um item de pedido de compra, para
-- que a entrada gerada por um recebimento seja rastreável até o pedido
-- (quantidade solicitada/atendida/pendente são calculadas via join, não
-- duplicadas aqui). A NF do recebimento é copiada para nota_fiscal.
ALTER TABLE entradas_estoque ADD COLUMN IF NOT EXISTS pedido_item_id INTEGER REFERENCES pedidos_compra_itens(id);

-- Movimentações: suporte a transferência entre obras (item 10), além da
-- transferência entre unidades já existente.
ALTER TABLE movimentacoes_consumiveis ADD COLUMN IF NOT EXISTS obra_origem_id INTEGER REFERENCES obras(id);
ALTER TABLE movimentacoes_consumiveis ADD COLUMN IF NOT EXISTS obra_destino_id INTEGER REFERENCES obras(id);
ALTER TABLE movimentacoes_patrimonio ADD COLUMN IF NOT EXISTS obra_origem_id INTEGER REFERENCES obras(id);
ALTER TABLE movimentacoes_patrimonio ADD COLUMN IF NOT EXISTS obra_destino_id INTEGER REFERENCES obras(id);
