from datetime import datetime, timezone
from app.extensions import db


class Property(db.Model):
    __tablename__ = "properties"

    property_id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    property_name = db.Column(db.String(150), nullable=False)
    property_type = db.Column(db.String(80), nullable=False)
    location = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    monthly_rent = db.Column(db.Numeric(12, 2), nullable=False)
    availability_status = db.Column(db.String(30), nullable=False, default="available")
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    owner = db.relationship("User", back_populates="properties")
    applications = db.relationship("RentalApplication", back_populates="property")
    tenancies = db.relationship("Tenancy", back_populates="property")
    maintenance_requests = db.relationship("MaintenanceRequest", back_populates="property")
