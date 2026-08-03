from flask import Flask, render_template, request, redirect, url_for, flash, g
from config import Config
import db as db_module
from auth import load_logged_in_user
from permissoes import MENU_CHAVES, menu_permitido


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    if not app.config["DATABASE_URL"]:
        raise RuntimeError(
            "A variável de ambiente DATABASE_URL não está definida. "
            "Configure-a com a string de conexão do PostgreSQL."
        )

    db_module.init_app(app)

    # Cria/atualiza as tabelas automaticamente (idempotente)
    db_module.init_db(app)

    # Registro dos módulos (blueprints) do sistema
    from blueprints.home import bp as home_bp
    from blueprints.auth import bp as auth_bp
    from blueprints.usuarios import bp as usuarios_bp
    from blueprints.dashboard import bp as dashboard_bp
    from blueprints.secretarias import bp as secretarias_bp
    from blueprints.unidades import bp as unidades_bp
    from blueprints.materiais import bp as materiais_bp
    from blueprints.fornecedores import bp as fornecedores_bp
    from blueprints.obras import bp as obras_bp
    from blueprints.patrimonio import bp as patrimonio_bp
    from blueprints.entradas import bp as entradas_bp
    from blueprints.mov_consumiveis import bp as mov_consumiveis_bp
    from blueprints.mov_patrimonio import bp as mov_patrimonio_bp
    from blueprints.estoque import bp as estoque_bp
    from blueprints.cotacoes import bp as cotacoes_bp
    from blueprints.solicitacoes_compra import bp as solicitacoes_compra_bp
    from blueprints.pedidos_compra import bp as pedidos_compra_bp
    from blueprints.licitacoes import bp as licitacoes_bp
    from blueprints.relatorios import bp as relatorios_bp
    from blueprints.auditoria import bp as auditoria_bp
    from blueprints.permissoes import bp as permissoes_bp

    app.register_blueprint(home_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(usuarios_bp, url_prefix="/usuarios")
    app.register_blueprint(permissoes_bp, url_prefix="/permissoes")
    app.register_blueprint(auditoria_bp, url_prefix="/auditoria")
    app.register_blueprint(relatorios_bp, url_prefix="/relatorios")

    # Módulo: Materiais e Patrimônio
    app.register_blueprint(dashboard_bp, url_prefix="/materiais-patrimonio")
    app.register_blueprint(secretarias_bp, url_prefix="/secretarias")
    app.register_blueprint(unidades_bp, url_prefix="/unidades")
    app.register_blueprint(materiais_bp, url_prefix="/materiais")
    app.register_blueprint(fornecedores_bp, url_prefix="/fornecedores")
    app.register_blueprint(obras_bp, url_prefix="/obras")
    app.register_blueprint(patrimonio_bp, url_prefix="/patrimonio")
    app.register_blueprint(entradas_bp, url_prefix="/entradas")
    app.register_blueprint(mov_consumiveis_bp, url_prefix="/movimentacoes-consumiveis")
    app.register_blueprint(mov_patrimonio_bp, url_prefix="/movimentacoes-patrimonio")
    app.register_blueprint(estoque_bp, url_prefix="/estoque")
    app.register_blueprint(solicitacoes_compra_bp, url_prefix="/solicitacoes-compra")
    app.register_blueprint(pedidos_compra_bp, url_prefix="/pedidos-compra")
    app.register_blueprint(licitacoes_bp, url_prefix="/licitacoes")

    # Módulo: Cotação x Projeto
    app.register_blueprint(cotacoes_bp, url_prefix="/cotacoes")

    @app.before_request
    def _carregar_usuario_logado():
        load_logged_in_user()

    @app.before_request
    def _exigir_login():
        if request.endpoint is None or request.endpoint.startswith("static"):
            return
        if request.endpoint in ("auth.login", "auth.setup"):
            return
        if db_module.query_one("SELECT COUNT(*) AS c FROM usuarios")["c"] == 0:
            return redirect(url_for("auth.setup"))
        if g.user is None:
            flash("Faça login para continuar.", "warning")
            return redirect(url_for("auth.login", next=request.path))

    @app.before_request
    def _exigir_permissao_menu():
        if request.endpoint is None or request.endpoint.startswith("static"):
            return
        if g.user is None:
            return  # _exigir_login já tratou (ou a rota é isenta de login)
        if request.blueprint in MENU_CHAVES and not menu_permitido(g.user, request.blueprint):
            flash("Você não tem permissão para acessar este módulo.", "danger")
            return redirect(url_for("home.index"))

    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    @app.context_processor
    def inject_globals():
        from datetime import date, datetime

        usuario_logado = g.get("user") if g else None
        return {
            "sistema_nome": app.config["SISTEMA_NOME"],
            "hoje": date.today().isoformat(),
            "agora": datetime.now().strftime("%Y-%m-%dT%H:%M"),
            "current_user": usuario_logado,
            "menu_permitido": lambda chave: menu_permitido(usuario_logado, chave),
        }

    @app.template_filter("brdate")
    def brdate(value, default="-"):
        """Converte uma data no formato ISO (YYYY-MM-DD) armazenada no banco
        para o formato brasileiro (DD/MM/AAAA)."""
        if not value:
            return default
        try:
            y, m, d = str(value)[:10].split("-")
            return f"{d}/{m}/{y}"
        except (ValueError, AttributeError):
            return value

    @app.template_filter("brdatetime")
    def brdatetime(value, default="-"):
        """Converte uma data/hora ISO (YYYY-MM-DDTHH:MM, ou só YYYY-MM-DD
        nos registros antigos) para o formato brasileiro (DD/MM/AAAA HH:MM)."""
        if not value:
            return default
        try:
            data_parte, _, hora_parte = str(value).partition("T")
            y, m, d = data_parte[:10].split("-")
            data_fmt = f"{d}/{m}/{y}"
            return f"{data_fmt} {hora_parte[:5]}" if hora_parte else data_fmt
        except (ValueError, AttributeError):
            return value

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
