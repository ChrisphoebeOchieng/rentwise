from app.extensions import db


class Tenancy(db.Model):
    __tablename__ = "tenancies"

    tenancy_id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.tenant_id"), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey("properties.property_id"), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    monthly_rent = db.Column(db.Numeric(12, 2), nullable=False)
    tenancy_status = db.Column(db.String(30), nullable=False, default="active")

    tenant = db.relationship("Tenant", back_populates="tenancies")
    property = db.relationship("Property", back_populates="tenancies")
    payments = db.relationship("Payment", back_populates="tenancy")
