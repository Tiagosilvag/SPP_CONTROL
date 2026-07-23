from flask import Blueprint, render_template, request
from services import calcular_estoque_consumiveis

bp = Blueprint("estoque", __name__)


@bp.route("/")
def listar():
    alerta = request.args.get("alerta", "")
    linhas = calcular_estoque_consumiveis()
    if alerta:
        linhas = [l for l in linhas if l["status_alerta"] == alerta]
    return render_template("estoque/list.html", linhas=linhas, alerta=alerta)
