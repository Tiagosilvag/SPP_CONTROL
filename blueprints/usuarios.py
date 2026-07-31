from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from db import query_all, query_one, execute
from auth import roles_required, hash_senha, PERFIS

bp = Blueprint("usuarios", __name__)


@bp.route("/")
@roles_required("Administrador")
def listar():
    usuarios = query_all(
        """SELECT u.*, uc.nome AS criado_por_nome
           FROM usuarios u LEFT JOIN usuarios uc ON uc.id = u.criado_por
           ORDER BY u.nome"""
    )
    return render_template("usuarios/list.html", usuarios=usuarios)


@bp.route("/novo", methods=["GET", "POST"])
@roles_required("Administrador")
def novo():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        if query_one("SELECT id FROM usuarios WHERE email=?", (email,)):
            flash("Já existe um usuário com este e-mail.", "danger")
            return redirect(url_for("usuarios.novo"))
        senha = request.form.get("senha", "")
        if len(senha) < 6:
            flash("A senha deve ter pelo menos 6 caracteres.", "danger")
            return redirect(url_for("usuarios.novo"))
        execute(
            """INSERT INTO usuarios (nome, email, senha_hash, perfil, ativo, criado_por)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                request.form["nome"].strip(),
                email,
                hash_senha(senha),
                request.form.get("perfil", "Operador"),
                1 if request.form.get("ativo") else 0,
                g.user["id"],
            ),
        )
        flash("Usuário cadastrado com sucesso.", "success")
        return redirect(url_for("usuarios.listar"))
    return render_template("usuarios/form.html", usuario=None, perfis=PERFIS)


@bp.route("/<int:id>/editar", methods=["GET", "POST"])
@roles_required("Administrador")
def editar(id):
    u = query_one("SELECT * FROM usuarios WHERE id=?", (id,))
    if u is None:
        flash("Usuário não encontrado.", "danger")
        return redirect(url_for("usuarios.listar"))
    if request.method == "POST":
        senha = request.form.get("senha", "").strip()
        if senha and len(senha) < 6:
            flash("A senha deve ter pelo menos 6 caracteres.", "danger")
            return redirect(url_for("usuarios.editar", id=id))

        if senha:
            execute(
                """UPDATE usuarios SET nome=?, perfil=?, ativo=?, senha_hash=? WHERE id=?""",
                (
                    request.form["nome"].strip(),
                    request.form.get("perfil", "Operador"),
                    1 if request.form.get("ativo") else 0,
                    hash_senha(senha),
                    id,
                ),
            )
        else:
            execute(
                """UPDATE usuarios SET nome=?, perfil=?, ativo=? WHERE id=?""",
                (
                    request.form["nome"].strip(),
                    request.form.get("perfil", "Operador"),
                    1 if request.form.get("ativo") else 0,
                    id,
                ),
            )
        flash("Usuário atualizado com sucesso.", "success")
        return redirect(url_for("usuarios.listar"))
    return render_template("usuarios/form.html", usuario=u, perfis=PERFIS)
