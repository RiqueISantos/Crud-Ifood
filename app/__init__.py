from flask import Flask
from flask_cors import CORS
from app.database import engine, Base
import app.models.models


def create_app():
    app = Flask(__name__)

    CORS(app, origins=["http://localhost:5173", "http://localhost:5174"])

    Base.metadata.create_all(bind=engine)

    from app.routes import usuario_bp

    app.register_blueprint(usuario_bp, url_prefix="/usuarios")

    return app
