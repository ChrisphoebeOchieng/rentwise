from app.extensions import db


class Payment(db.Model):
    __tablename__ = "payments"

    payment_id = db.Column(db.Integer, primary_key=True)
    tenancy_id = db.Column(db.Integer, db.ForeignKey("tenancies.tenancy_id"), nullable=False)
    amount_due = db.Column(db.Numeric(12, 2), nullable=False)
    amount_paid = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    payment_date = db.Column(db.DateTime(timezone=True))
    payment_method = db.Column(db.String(50))
    transaction_reference = db.Column(db.String(100), unique=True)
    payment_status = db.Column(db.String(30), nullable=False, default="pending")

    tenancy = db.relationship("Tenancy", back_populates="payments")
