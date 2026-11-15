from datetime import datetime, timezone
from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    user_id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    phone_number = db.Column(db.String(20))
    password_hash = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.role_id"), nullable=False)
    account_status = db.Column(db.String(30), nullable=False, default="active")
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    role = db.relationship("Role", back_populates="users")
    properties = db.relationship("Property", back_populates="owner")
    applications = db.relationship("RentalApplication", back_populates="applicant")
    tenant = db.relationship("Tenant", back_populates="user", uselist=False)
    notifications = db.relationship("Notification", back_populates="user")
