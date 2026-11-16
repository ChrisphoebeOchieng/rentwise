from app.extensions import db
from app.models import Notification


def create_notification(user_id, message, notification_type):
    notification = Notification(
        user_id=user_id,
        message=message,
        notification_type=notification_type,
        read_status=False
    )

    db.session.add(notification)
    return notification
