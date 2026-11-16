from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from app.extensions import db
from app.models import RentalApplication, Property
from app.services.notifications import create_notification
from app.utils.permissions import role_required


applications_bp = Blueprint(
    "applications",
    __name__,
    url_prefix="/api/applications"
)


def application_response(application):
    return {
        "application_id": application.application_id,
        "property_id": application.property_id,
        "property_name": application.property.property_name,
        "property_location": application.property.location,
        "monthly_rent": str(application.property.monthly_rent),
        "applicant_id": application.applicant_id,
        "applicant_name": application.applicant.full_name,
        "application_date": (
            application.application_date.isoformat()
            if application.application_date else None
        ),
        "application_status": application.application_status,
        "review_comments": application.review_comments
    }


def get_application_access(application_id):
    application = db.session.get(RentalApplication, application_id)

    if not application:
        return None, (jsonify({
            "success": False,
            "message": "Rental application not found."
        }), 404)

    user = request.current_user
    role = user.role.role_name

    if role == "Administrator":
        return application, None

    if role == "Tenant" and application.applicant_id == user.user_id:
        return application, None

    if role == "Landlord" and application.property.owner_id == user.user_id:
        return application, None

    return None, (jsonify({
        "success": False,
        "message": "You do not have permission to access this application."
    }), 403)


@applications_bp.post("")
@jwt_required()
@role_required("Tenant")
def submit_application():
    data = request.get_json(silent=True) or {}
    property_id = data.get("property_id")

    try:
        property_id = int(property_id)
    except (TypeError, ValueError):
        return jsonify({
            "success": False,
            "message": "A valid property ID is required."
        }), 400

    property = db.session.get(Property, property_id)

    if not property:
        return jsonify({
            "success": False,
            "message": "Property not found."
        }), 404

    if property.availability_status != "available":
        return jsonify({
            "success": False,
            "message": "This property is not currently available."
        }), 409

    existing_application = RentalApplication.query.filter(
        RentalApplication.property_id == property_id,
        RentalApplication.applicant_id == request.current_user.user_id,
        RentalApplication.application_status.in_(["pending", "approved"])
    ).first()

    if existing_application:
        return jsonify({
            "success": False,
            "message": "You already have an active application for this property."
        }), 409

    application = RentalApplication(
        property_id=property_id,
        applicant_id=request.current_user.user_id,
        application_status="pending"
    )

    try:
        db.session.add(application)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Rental application submitted successfully.",
            "application": application_response(application)
        }), 201

    except Exception:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Unable to submit rental application."
        }), 500


@applications_bp.get("")
@jwt_required()
@role_required("Tenant", "Landlord", "Administrator")
def list_applications():
    user = request.current_user
    role = user.role.role_name

    query = RentalApplication.query

    if role == "Tenant":
        query = query.filter_by(applicant_id=user.user_id)

    elif role == "Landlord":
        query = query.join(Property).filter(
            Property.owner_id == user.user_id
        )

    applications = query.order_by(
        RentalApplication.application_date.desc()
    ).all()

    return jsonify({
        "success": True,
        "count": len(applications),
        "applications": [
            application_response(application)
            for application in applications
        ]
    }), 200


@applications_bp.get("/<int:application_id>")
@jwt_required()
@role_required("Tenant", "Landlord", "Administrator")
def get_application(application_id):
    application, error = get_application_access(application_id)

    if error:
        return error

    return jsonify({
        "success": True,
        "application": application_response(application)
    }), 200


@applications_bp.patch("/<int:application_id>/review")
@jwt_required()
@role_required("Landlord", "Administrator")
def review_application(application_id):
    application, error = get_application_access(application_id)

    if error:
        return error

    if application.application_status != "pending":
        return jsonify({
            "success": False,
            "message": "Only pending applications can be reviewed."
        }), 409

    data = request.get_json(silent=True) or {}
    status = (data.get("application_status") or "").strip().lower()
    comments = (data.get("review_comments") or "").strip() or None

    if status not in ("approved", "rejected"):
        return jsonify({
            "success": False,
            "message": "Application status must be approved or rejected."
        }), 400

    application.application_status = status
    application.review_comments = comments
    create_notification(
        user_id=application.applicant_id,
        message=(
            f'Your rental application for '
            f'{application.property.property_name} has been {status}.'
        ),
        notification_type='application'
    )

    try:
        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"Rental application {status} successfully.",
            "application": application_response(application)
        }), 200

    except Exception:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Unable to review rental application."
        }), 500
