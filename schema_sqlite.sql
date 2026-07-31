-- Schema histórico usado apenas por seed_data.py para (re)gerar um banco
-- SQLite local a partir da planilha original. O banco de produção da
-- aplicação usa PostgreSQL (veja schema.sql).

CREATE TABLE IF NOT EXISTS secretarias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    sigla TEXT NOT NULL,
    responsavel TEXT,
    contato TEXT,
    ativa INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS unidades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    secretaria_id INTEGER NOT NULL REFERENCES secretarias(id),
    nome TEXT NOT NULL,
    endereco TEXT,
    responsavel_local TEXT,
    ativa INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS materiais (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    tipo_material TEXT NOT NULL,      -- 'Consumível' ou 'Patrimonial'
    categoria TEXT,
    unidade_medida TEXT,
    estoque_minimo REAL DEFAULT 0,
    ativo INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS fornecedores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    cnpj TEXT,
    contato TEXT,
    ativo INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS obras (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data_entrada TEXT NOT NULL,
    material_id INTEGER NOT NULL REFERENCES materiais(id),
    secretaria_proprietaria_id INTEGER REFERENCES secretarias(id),
    unidade_destino_id INTEGER REFERENCES unidades(id),
    fornecedor_id INTEGER REFERENCES fornecedores(id),
    quantidade REAL NOT NULL,
    nota_fiscal TEXT,
    obra_id INTEGER REFERENCES obras(id),
    observacoes TEXT
);

CREATE TABLE IF NOT EXISTS movimentacoes_consumiveis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data_movimentacao TEXT NOT NULL,
    tipo_movimentacao TEXT NOT NULL,
    material_id INTEGER NOT NULL REFERENCES materiais(id),
    quantidade REAL NOT NULL,
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
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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

CREATE TABLE IF NOT EXISTS cotacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    obra_id INTEGER NOT NULL REFERENCES obras(id),
    fornecedor_id INTEGER REFERENCES fornecedores(id),
    descricao TEXT NOT NULL,
    valor_cotado REAL NOT NULL,
    valor_economizado REAL NOT NULL DEFAULT 0,
    data_cotacao TEXT,
    observacoes TEXT
);

CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    senha_hash TEXT NOT NULL,
    perfil TEXT DEFAULT 'Operador',
    ativo INTEGER NOT NULL DEFAULT 1
);
