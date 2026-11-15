from datetime import datetime, timezone
from app.extensions import db


class RentalApplication(db.Model):
    __tablename__ = "rental_applications"

    application_id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey("properties.property_id"), nullable=False)
    applicant_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    application_date = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    application_status = db.Column(db.String(30), nullable=False, default="pending")
    review_comments = db.Column(db.Text)

    property = db.relationship("Property", back_populates="applications")
    applicant = db.relationship("User", back_populates="applications")
