from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from sqlalchemy import func

from app.extensions import db, bcrypt
from app.models import User, Role

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def user_response(user):
    return {
        "user_id": user.user_id,
        "full_name": user.full_name,
        "email": user.email,
        "phone_number": user.phone_number,
        "role": user.role.role_name,
        "account_status": user.account_status
    }


@auth_bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}

    full_name = (data.get("full_name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    phone_number = (data.get("phone_number") or "").strip() or None

    if not full_name or not email or not password:
        return jsonify({
            "success": False,
            "message": "Full name, email and password are required."
        }), 400

    if len(password) < 8:
        return jsonify({
            "success": False,
            "message": "Password must contain at least 8 characters."
        }), 400

    if "@" not in email:
        return jsonify({
            "success": False,
            "message": "Please provide a valid email address."
        }), 400

    existing_user = db.session.query(User).filter(
        func.lower(User.email) == email
    ).first()

    if existing_user:
        return jsonify({
            "success": False,
            "message": "An account with this email already exists."
        }), 409

    tenant_role = Role.query.filter_by(role_name="Tenant").first()

    if not tenant_role:
        return jsonify({
            "success": False,
            "message": "System roles have not been initialized."
        }), 500

    password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    user = User(
        full_name=full_name,
        email=email,
        phone_number=phone_number,
        password_hash=password_hash,
        role_id=tenant_role.role_id
    )

    try:
        db.session.add(user)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Account created successfully.",
            "user": user_response(user)
        }), 201

    except Exception:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Unable to create account."
        }), 500


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({
            "success": False,
            "message": "Email and password are required."
        }), 400

    user = db.session.query(User).filter(
        func.lower(User.email) == email
    ).first()

    if not user or not bcrypt.check_password_hash(user.password_hash, password):
        return jsonify({
            "success": False,
            "message": "Invalid email or password."
        }), 401

    if user.account_status != "active":
        return jsonify({
            "success": False,
            "message": "This account is not active. Contact an administrator."
        }), 403

    access_token = create_access_token(identity=str(user.user_id))

    return jsonify({
        "success": True,
        "message": "Login successful.",
        "access_token": access_token,
        "user": user_response(user)
    }), 200


@auth_bp.get("/me")
@jwt_required()
def get_current_user():
    user_id = get_jwt_identity()
    user = db.session.get(User, int(user_id))

    if not user:
        return jsonify({
            "success": False,
            "message": "User account not found."
        }), 404

    return jsonify({
        "success": True,
        "user": user_response(user)
    }), 200
