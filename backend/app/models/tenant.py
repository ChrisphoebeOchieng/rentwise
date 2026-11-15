from app.extensions import db


class Tenant(db.Model):
    __tablename__ = "tenants"

    tenant_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False, unique=True)
    identification_number = db.Column(db.String(50), unique=True)
    emergency_contact = db.Column(db.String(100))

    user = db.relationship("User", back_populates="tenant")
    tenancies = db.relationship("Tenancy", back_populates="tenant")
    maintenance_requests = db.relationship("MaintenanceRequest", back_populates="tenant")
