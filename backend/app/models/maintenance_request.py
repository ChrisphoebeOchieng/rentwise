from datetime import datetime, timezone
from app.extensions import db


class MaintenanceRequest(db.Model):
    __tablename__ = "maintenance_requests"

    request_id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey("properties.property_id"), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.tenant_id"), nullable=False)
    description = db.Column(db.Text, nullable=False)
    request_date = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    priority = db.Column(db.String(30), nullable=False, default="normal")
    request_status = db.Column(db.String(30), nullable=False, default="pending")
    resolution_details = db.Column(db.Text)

    property = db.relationship("Property", back_populates="maintenance_requests")
    tenant = db.relationship("Tenant", back_populates="maintenance_requests")
