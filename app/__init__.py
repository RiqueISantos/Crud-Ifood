import os
from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from dotenv import load_dotenv
from .database import db
from .routes import usuario_bp

load_dotenv()


def create_app():
    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = (
        os.getenv("DATABASE_URL", "postgresql://postgres:password123@localhost:5432/db_ifood")
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY_FLASK", "ifood_flask_secret_2026")

    db.init_app(app)
    Migrate(app, db)
    CORS(app, origins=["http://localhost:5173", "http://localhost:5174"])

    # As tabelas são gerenciadas pelo Flask-Migrate (flask db upgrade)
    # Não usar db.create_all() aqui para evitar conflitos com migrations

    from .routes.oauth_routes import oauth_bp
    from .routes.endereco_routes import endereco_bp
    from .routes.restaurante_routes import restaurante_bp

    app.register_blueprint(usuario_bp, url_prefix="/usuarios")
    app.register_blueprint(oauth_bp)
    app.register_blueprint(endereco_bp, url_prefix="/enderecos")
    app.register_blueprint(restaurante_bp, url_prefix="/restaurantes")

    return app
