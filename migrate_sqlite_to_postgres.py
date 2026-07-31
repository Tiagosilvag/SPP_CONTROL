"""
Migra os dados existentes do banco SQLite (instance/spp_control.db) para o
PostgreSQL, preservando os IDs originais.

Uso:
    DATABASE_URL="postgresql://usuario:senha@host:porta/banco" python migrate_sqlite_to_postgres.py

Este script:
  1. Cria as tabelas no PostgreSQL (a partir de schema.sql), caso não existam.
  2. Copia os dados de cada tabela do SQLite para o PostgreSQL.
  3. Reajusta as sequences (SERIAL) do PostgreSQL para continuar a partir do
     maior ID já existente, evitando conflitos em novos INSERTs feitos pela
     aplicação.

Rode esse script apenas uma vez, contra um banco PostgreSQL vazio (recém-criado).
"""
import os
import sqlite3
import psycopg2

SQLITE_PATH = os.path.join(os.path.dirname(__file__), "instance", "spp_control.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")

# Ordem que respeita as dependências de chave estrangeira (pai antes do filho)
TABLES = [
    "secretarias",
    "unidades",
    "materiais",
    "fornecedores",
    "obras",
    "patrimonios",
    "entradas_estoque",
    "movimentacoes_consumiveis",
    "movimentacoes_patrimonio",
    "cotacoes",
    "usuarios",
]


def run():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("Defina a variável de ambiente DATABASE_URL antes de rodar este script.")
    if not os.path.exists(SQLITE_PATH):
        raise SystemExit(f"Banco SQLite não encontrado em {SQLITE_PATH}.")

    sconn = sqlite3.connect(SQLITE_PATH)
    sconn.row_factory = sqlite3.Row

    pconn = psycopg2.connect(database_url)
    pcur = pconn.cursor()

    print("Criando tabelas no PostgreSQL (se ainda não existirem)...")
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        pcur.execute(f.read())
    pconn.commit()

    print("Limpando tabelas de destino antes de copiar os dados...")
    pcur.execute("TRUNCATE " + ", ".join(TABLES) + " RESTART IDENTITY CASCADE")
    pconn.commit()

    print("Copiando dados:")
    for table in TABLES:
        rows = sconn.execute(f"SELECT * FROM {table}").fetchall()
        if not rows:
            print(f"  {table}: 0 linha(s)")
            continue

        columns = rows[0].keys()
        col_list = ", ".join(columns)
        placeholders = ", ".join(["%s"] * len(columns))

        for row in rows:
            values = [row[c] for c in columns]
            pcur.execute(
                f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})",
                values,
            )

        if "id" in columns:
            pcur.execute(
                f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                f"(SELECT MAX(id) FROM {table}))"
            )

        print(f"  {table}: {len(rows)} linha(s) migradas")

    pconn.commit()
    pcur.close()
    pconn.close()
    sconn.close()
    print("Migração concluída com sucesso.")


if __name__ == "__main__":
    run()
