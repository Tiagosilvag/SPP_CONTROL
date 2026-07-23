import os
from flask import Flask, render_template
from config import Config
import db as db_module


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    os.makedirs(os.path.dirname(app.config["DATABASE_PATH"]), exist_ok=True)
    db_module.init_app(app)

    # Cria as tabelas automaticamente caso o banco ainda não exista
    if not os.path.exists(app.config["DATABASE_PATH"]):
        db_module.init_db(app)

    # Registro dos módulos (blueprints) do sistema
    from blueprints.home import bp as home_bp
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

    app.register_blueprint(home_bp)

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

    # Módulo: Cotação x Projeto
    app.register_blueprint(cotacoes_bp, url_prefix="/cotacoes")

    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    @app.context_processor
    def inject_globals():
        from datetime import date
        return {"sistema_nome": app.config["SISTEMA_NOME"], "hoje": date.today().isoformat()}

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

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
