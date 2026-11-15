import click
from flask import Flask, jsonify

from app.config import Config
from app.extensions import db, migrate, jwt, bcrypt, cors


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    from app import models
    from app.routes.auth import auth_bp
    from app.routes.properties import properties_bp
    from app.routes.applications import applications_bp
    from app.routes.tenancies import tenancies_bp
    from app.routes.payments import payments_bp
    from app.routes.maintenance import maintenance_bp

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    bcrypt.init_app(app)

    cors.init_app(
        app,
        resources={r"/api/*": {"origins": ["http://localhost:5173"]}}
    )

    app.register_blueprint(auth_bp)
    app.register_blueprint(properties_bp)
    app.register_blueprint(applications_bp)
    app.register_blueprint(tenancies_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(maintenance_bp)

    @app.get("/api/health")
    def health_check():
        return jsonify({
            "success": True,
            "message": "RentWise API is running",
            "application": "RentWise"
        }), 200

    @app.cli.command("seed-roles")
    def seed_roles():
        roles = {
            "Administrator": "Manages system users and platform operations.",
            "Landlord": "Manages owned rental properties and rental activities.",
            "Property Manager": "Manages assigned properties and tenancy operations.",
            "Tenant": "Accesses tenancy information and rental services."
        }

        for role_name, description in roles.items():
            existing = models.Role.query.filter_by(
                role_name=role_name
            ).first()

            if not existing:
                db.session.add(models.Role(
                    role_name=role_name,
                    description=description
                ))

        db.session.commit()
        click.echo("RentWise roles initialized successfully.")

    return app
