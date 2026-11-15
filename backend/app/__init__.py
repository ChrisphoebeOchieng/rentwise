from flask import Flask, jsonify
from app.config import Config
from app.extensions import db, migrate, jwt, bcrypt, cors


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    from app import models

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    bcrypt.init_app(app)

    cors.init_app(
        app,
        resources={r"/api/*": {"origins": ["http://localhost:5173"]}}
    )

    @app.get("/api/health")
    def health_check():
        return jsonify({
            "success": True,
            "message": "RentWise API is running",
            "application": "RentWise"
        }), 200

    return app
