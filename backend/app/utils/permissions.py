from functools import wraps

from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity

from app.models import User


def role_required(*allowed_roles):
    def decorator(view_function):
        @wraps(view_function)
        def wrapper(*args, **kwargs):
            user_id = get_jwt_identity()
            user = User.query.get(int(user_id))

            if not user:
                return jsonify({
                    "success": False,
                    "message": "User account not found."
                }), 404

            if user.account_status != "active":
                return jsonify({
                    "success": False,
                    "message": "Your account is not active."
                }), 403

            if not user.role or user.role.role_name not in allowed_roles:
                return jsonify({
                    "success": False,
                    "message": "You do not have permission to perform this action."
                }), 403

            request.current_user = user
            return view_function(*args, **kwargs)

        return wrapper
    return decorator
