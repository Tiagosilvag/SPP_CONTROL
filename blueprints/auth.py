from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g
from db import query_one, query_all, execute
from auth import verificar_senha, hash_senha

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("dashboard.index"))

    total_usuarios = query_one("SELECT COUNT(*) AS c FROM usuarios")["c"]
    if total_usuarios == 0:
        return redirect(url_for("auth.setup"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")
        user = query_one("SELECT * FROM usuarios WHERE email=?", (email,))
        if user is None or not user["ativo"] or not verificar_senha(user["senha_hash"], senha):
            flash("E-mail ou senha inválidos.", "danger")
            return redirect(url_for("auth.login"))

        session.clear()
        session["user_id"] = user["id"]
        execute(
            "UPDATE usuarios SET ultimo_acesso=? WHERE id=?",
            (datetime.now().isoformat(), user["id"]),
            audit=False,
        )
        flash(f"Bem-vindo(a), {user['nome']}!", "success")
        next_url = request.args.get("next") or url_for("dashboard.index")
        return redirect(next_url)

    return render_template("auth/login.html")


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Sessão encerrada.", "success")
    return redirect(url_for("auth.login"))


@bp.route("/setup", methods=["GET", "POST"])
def setup():
    """Cria a primeira conta de Administrador. Só funciona enquanto a
    tabela de usuários estiver vazia — depois disso vira uma rota morta."""
    total_usuarios = query_one("SELECT COUNT(*) AS c FROM usuarios")["c"]
    if total_usuarios > 0:
        flash("A configuração inicial já foi concluída. Faça login normalmente.", "info")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")
        if len(senha) < 6:
            flash("A senha deve ter pelo menos 6 caracteres.", "danger")
            return redirect(url_for("auth.setup"))

        user_id = execute(
            """INSERT INTO usuarios (nome, email, senha_hash, perfil, ativo)
               VALUES (?, ?, ?, 'Administrador', 1)""",
            (nome, email, hash_senha(senha)),
            audit=False,
        )
        session.clear()
        session["user_id"] = user_id
        flash("Conta de administrador criada com sucesso!", "success")
        return redirect(url_for("dashboard.index"))

    return render_template("auth/setup.html")
