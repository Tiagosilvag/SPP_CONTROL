from flask import Blueprint, render_template, request, redirect, url_for, flash
from db import query_all, query_one
from auth import roles_required
from permissoes import MENU_ITEMS, permissoes_efetivas, salvar_permissoes, restaurar_padrao

bp = Blueprint("permissoes", __name__)


@bp.route("/")
@roles_required("Administrador")
def listar():
    usuarios = query_all("SELECT * FROM usuarios WHERE perfil != 'Administrador' ORDER BY nome")
    return render_template("permissoes/list.html", usuarios=usuarios)


@bp.route("/<int:id>", methods=["GET", "POST"])
@roles_required("Administrador")
def editar(id):
    usuario = query_one("SELECT * FROM usuarios WHERE id=?", (id,))
    if usuario is None:
        flash("Usuário não encontrado.", "danger")
        return redirect(url_for("permissoes.listar"))
    if usuario["perfil"] == "Administrador":
        flash("Administradores sempre têm acesso a todos os menus — não é configurável.", "info")
        return redirect(url_for("permissoes.listar"))

    if request.method == "POST":
        if request.form.get("acao") == "restaurar":
            restaurar_padrao(id)
            flash(f"Permissões de {usuario['nome']} restauradas para o padrão do perfil.", "success")
        else:
            chaves = request.form.getlist("menu")
            salvar_permissoes(id, chaves)
            flash(f"Permissões de {usuario['nome']} atualizadas com sucesso.", "success")
        return redirect(url_for("permissoes.listar"))

    permitidos = permissoes_efetivas(usuario)
    grupos = {}
    for item in MENU_ITEMS:
        grupos.setdefault(item["grupo"], []).append(item)

    return render_template(
        "permissoes/form.html",
        usuario=usuario,
        grupos=grupos,
        permitidos=permitidos,
        customizado=usuario["permissoes_customizadas"],
    )
