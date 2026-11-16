from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from app.extensions import db
from app.models import Notification
from app.utils.permissions import role_required


notifications_bp = Blueprint(
    "notifications",
    __name__,
    url_prefix="/api/notifications"
)


def notification_response(notification):
    return {
        "notification_id": notification.notification_id,
        "message": notification.message,
        "notification_type": notification.notification_type,
        "created_at": (
            notification.created_at.isoformat()
            if notification.created_at else None
        ),
        "read_status": notification.read_status
    }


@notifications_bp.get("")
@jwt_required()
@role_required("Administrator", "Landlord", "Property Manager", "Tenant")
def list_notifications():
    user = request.current_user

    query = Notification.query.filter_by(user_id=user.user_id)

    unread_only = request.args.get("unread_only", "false").lower()

    if unread_only == "true":
        query = query.filter_by(read_status=False)

    notifications = query.order_by(
        Notification.created_at.desc()
    ).all()

    return jsonify({
        "success": True,
        "count": len(notifications),
        "unread_count": Notification.query.filter_by(
            user_id=user.user_id,
            read_status=False
        ).count(),
        "notifications": [
            notification_response(item) for item in notifications
        ]
    }), 200


@notifications_bp.patch("/read-all")
@jwt_required()
@role_required("Administrator", "Landlord", "Property Manager", "Tenant")
def mark_all_notifications_read():
    user = request.current_user

    Notification.query.filter_by(
        user_id=user.user_id,
        read_status=False
    ).update({"read_status": True})

    db.session.commit()

    return jsonify({
        "success": True,
        "message": "All notifications marked as read."
    }), 200


@notifications_bp.patch("/<int:notification_id>/read")
@jwt_required()
@role_required("Administrator", "Landlord", "Property Manager", "Tenant")
def mark_notification_read(notification_id):
    user = request.current_user

    notification = db.session.get(Notification, notification_id)

    if not notification:
        return jsonify({
            "success": False,
            "message": "Notification not found."
        }), 404

    if notification.user_id != user.user_id:
        return jsonify({
            "success": False,
            "message": "You do not have permission to access this notification."
        }), 403

    notification.read_status = True
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Notification marked as read.",
        "notification": notification_response(notification)
    }), 200
