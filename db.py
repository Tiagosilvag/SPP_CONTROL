import os
import psycopg2
import psycopg2.extras
from flask import g, current_app

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


def _to_pg(sql):
    """Converte os placeholders '?' (estilo sqlite) para '%s' (estilo psycopg2)."""
    return sql.replace("?", "%s")


def get_db():
    if "db" not in g:
        g.db = psycopg2.connect(current_app.config["DATABASE_URL"])
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_app(app):
    app.teardown_appcontext(close_db)


def init_db(app):
    """Cria as tabelas caso ainda não existam."""
    with app.app_context():
        db = get_db()
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            with db.cursor() as cur:
                cur.execute(f.read())
        db.commit()


def query_all(sql, args=()):
    db = get_db()
    with db.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(_to_pg(sql), args)
        return cur.fetchall()


def query_one(sql, args=()):
    db = get_db()
    with db.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(_to_pg(sql), args)
        return cur.fetchone()


def execute(sql, args=()):
    """Executa INSERT/UPDATE/DELETE. Para INSERT, retorna o id gerado
    (equivalente ao lastrowid do sqlite3), usando RETURNING id."""
    db = get_db()
    pg_sql = _to_pg(sql)
    is_insert = pg_sql.strip().upper().startswith("INSERT") and "RETURNING" not in pg_sql.upper()
    if is_insert:
        pg_sql += " RETURNING id"
    with db.cursor() as cur:
        cur.execute(pg_sql, args)
        result = cur.fetchone()[0] if is_insert else None
    db.commit()
    return result
