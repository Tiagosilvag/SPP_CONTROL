import functools
from flask import g, session, redirect, url_for, flash, request
from werkzeug.security import generate_password_hash, check_password_hash

PERFIS = ["Administrador", "Gestor", "Operador"]


def hash_senha(senha):
    return generate_password_hash(senha)


def verificar_senha(senha_hash, senha):
    return check_password_hash(senha_hash, senha)


def load_logged_in_user():
    from db import query_one

    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
    else:
        g.user = query_one("SELECT * FROM usuarios WHERE id=? AND ativo=1", (user_id,))
        if g.user is None:
            session.clear()


def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("Faça login para continuar.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def roles_required(*perfis):
    def decorator(view):
        @functools.wraps(view)
        def wrapped(*args, **kwargs):
            if g.user is None:
                flash("Faça login para continuar.", "warning")
                return redirect(url_for("auth.login", next=request.path))
            if g.user["perfil"] not in perfis:
                flash("Você não tem permissão para acessar esta página.", "danger")
                return redirect(url_for("dashboard.index"))
            return view(*args, **kwargs)

        return wrapped

    return decorator
