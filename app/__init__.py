import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from .database import db
from .routes import usuario_bp

load_dotenv()


def create_app():
    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = (
        os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/crud_usuarios")
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY_FLASK", "ifood_flask_secret_2026")

    db.init_app(app)
    CORS(app, origins=["http://localhost:5173", "http://localhost:5174"])

    with app.app_context():
        db.create_all()

    from .routes.oauth_routes import oauth_bp
    from .routes.endereco_routes import endereco_bp

    app.register_blueprint(usuario_bp, url_prefix="/usuarios")
    app.register_blueprint(oauth_bp)
    app.register_blueprint(endereco_bp, url_prefix="/enderecos")

    return app
