from flask import Flask
from flask_cors import CORS
from .database import db
from .routes import usuario_bp


def create_app():
    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = (
        "postgresql://postgres:postgres@localhost:5432/crud_usuarios"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    CORS(app, origins=["http://localhost:5173"])

    with app.app_context():
        db.create_all()

    app.register_blueprint(usuario_bp, url_prefix="/usuarios")

    return app
