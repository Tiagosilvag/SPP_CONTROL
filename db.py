import os
import re
import json
import psycopg2
import psycopg2.extras
from flask import g, current_app, request

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")

_TABLE_RE = re.compile(
    r"^\s*(INSERT INTO|UPDATE|DELETE FROM)\s+(\w+)", re.IGNORECASE
)
_WHERE_ID_RE = re.compile(r"WHERE\s+id\s*=\s*%s\s*$", re.IGNORECASE)


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
    """Cria/atualiza as tabelas caso ainda não existam (idempotente)."""
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


def _current_user_info():
    try:
        user = g.get("user")
    except RuntimeError:
        return None, None
    if user:
        return user["id"], user["nome"]
    return None, None


def _client_ip():
    try:
        return request.headers.get("X-Forwarded-For", request.remote_addr)
    except RuntimeError:
        return None


def _fetch_row_as_dict(cur, table, record_id):
    if record_id is None:
        return None
    cur.execute(f"SELECT * FROM {table} WHERE id = %s", (record_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def _log_auditoria(cur, operacao, tabela, registro_id, valor_anterior, valor_novo):
    usuario_id, usuario_nome = _current_user_info()
    cur.execute(
        """INSERT INTO auditoria (usuario_id, usuario_nome, ip, operacao, tabela, registro_id,
           valor_anterior, valor_novo)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
        (
            usuario_id,
            usuario_nome,
            _client_ip(),
            operacao,
            tabela,
            registro_id,
            json.dumps(valor_anterior, default=str, ensure_ascii=False) if valor_anterior is not None else None,
            json.dumps(valor_novo, default=str, ensure_ascii=False) if valor_novo is not None else None,
        ),
    )


def execute(sql, args=(), audit=True):
    """Executa INSERT/UPDATE/DELETE. Para INSERT, retorna o id gerado
    (equivalente ao lastrowid do sqlite3), usando RETURNING id.

    Quando audit=True (padrão) e a tabela não é 'auditoria', registra a
    operação em auditoria dentro da mesma transação. A captura de
    valor_anterior/valor_novo só é possível quando a query segue o padrão
    'WHERE id=?' usado em todo o projeto (o id é sempre o último argumento).
    """
    db = get_db()
    pg_sql = _to_pg(sql)
    match = _TABLE_RE.match(pg_sql)
    operacao, tabela = (match.group(1).split()[0].upper(), match.group(2)) if match else (None, None)
    is_insert = operacao == "INSERT" and "RETURNING" not in pg_sql.upper()
    if is_insert:
        pg_sql += " RETURNING id"

    do_audit = audit and tabela and tabela != "auditoria"
    record_id = args[-1] if (do_audit and operacao in ("UPDATE", "DELETE") and args) else None
    has_id_where = bool(_WHERE_ID_RE.search(pg_sql.strip()))

    with db.cursor() as cur:
        valor_anterior = None
        if do_audit and operacao == "UPDATE" and has_id_where:
            valor_anterior = _fetch_row_as_dict(cur, tabela, record_id)
        elif do_audit and operacao == "DELETE" and has_id_where:
            valor_anterior = _fetch_row_as_dict(cur, tabela, record_id)

        cur.execute(pg_sql, args)
        result = cur.fetchone()[0] if is_insert else None

        if do_audit:
            if operacao == "INSERT":
                valor_novo = _fetch_row_as_dict(cur, tabela, result)
                _log_auditoria(cur, "INSERT", tabela, result, None, valor_novo)
            elif operacao == "UPDATE":
                valor_novo = _fetch_row_as_dict(cur, tabela, record_id) if has_id_where else None
                _log_auditoria(cur, "UPDATE", tabela, record_id, valor_anterior, valor_novo)
            elif operacao == "DELETE":
                _log_auditoria(cur, "DELETE", tabela, record_id, valor_anterior, None)

    db.commit()
    return result
