from datetime import date
from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from app.extensions import db
from app.models import Tenancy, Tenant, Property, RentalApplication
from app.utils.permissions import role_required


tenancies_bp = Blueprint(
    "tenancies",
    __name__,
    url_prefix="/api/tenancies"
)


def tenancy_response(tenancy):
    return {
        "tenancy_id": tenancy.tenancy_id,
        "tenant_id": tenancy.tenant_id,
        "tenant_name": tenancy.tenant.user.full_name,
        "property_id": tenancy.property_id,
        "property_name": tenancy.property.property_name,
        "property_location": tenancy.property.location,
        "start_date": tenancy.start_date.isoformat(),
        "end_date": tenancy.end_date.isoformat() if tenancy.end_date else None,
        "monthly_rent": str(tenancy.monthly_rent),
        "tenancy_status": tenancy.tenancy_status
    }


def get_tenancy_access(tenancy_id):
    tenancy = db.session.get(Tenancy, tenancy_id)

    if not tenancy:
        return None, (jsonify({
            "success": False,
            "message": "Tenancy record not found."
        }), 404)

    user = request.current_user
    role = user.role.role_name

    if role == "Administrator":
        return tenancy, None

    if role == "Tenant" and tenancy.tenant.user_id == user.user_id:
        return tenancy, None

    if role == "Landlord" and tenancy.property.owner_id == user.user_id:
        return tenancy, None

    return None, (jsonify({
        "success": False,
        "message": "You do not have permission to access this tenancy."
    }), 403)


@tenancies_bp.post("")
@jwt_required()
@role_required("Landlord", "Administrator")
def create_tenancy():
    data = request.get_json(silent=True) or {}

    try:
        application_id = int(data.get("application_id"))
    except (TypeError, ValueError):
        return jsonify({
            "success": False,
            "message": "A valid application ID is required."
        }), 400

    application = db.session.get(RentalApplication, application_id)

    if not application:
        return jsonify({
            "success": False,
            "message": "Rental application not found."
        }), 404

    user = request.current_user

    if (
        user.role.role_name == "Landlord"
        and application.property.owner_id != user.user_id
    ):
        return jsonify({
            "success": False,
            "message": "You cannot create a tenancy for another landlord's property."
        }), 403

    if application.application_status != "approved":
        return jsonify({
            "success": False,
            "message": "Only approved applications can create a tenancy."
        }), 409

    property = application.property

    if property.availability_status != "available":
        return jsonify({
            "success": False,
            "message": "This property is not available for a new tenancy."
        }), 409

    existing_tenancy = Tenancy.query.filter_by(
        property_id=property.property_id,
        tenancy_status="active"
    ).first()

    if existing_tenancy:
        return jsonify({
            "success": False,
            "message": "This property already has an active tenancy."
        }), 409

    try:
        start_date = date.fromisoformat(data.get("start_date", ""))
        end_date_value = data.get("end_date")
        end_date = date.fromisoformat(end_date_value) if end_date_value else None

        if end_date and end_date <= start_date:
            raise ValueError

        monthly_rent = Decimal(str(
            data.get("monthly_rent", property.monthly_rent)
        ))

        if not monthly_rent.is_finite() or monthly_rent <= 0:
            raise InvalidOperation

    except (TypeError, ValueError, InvalidOperation):
        return jsonify({
            "success": False,
            "message": "Provide valid dates and a positive monthly rent. End date must be after start date."
        }), 400

    tenant = Tenant.query.filter_by(
        user_id=application.applicant_id
    ).first()

    try:
        if not tenant:
            tenant = Tenant(user_id=application.applicant_id)
            db.session.add(tenant)
            db.session.flush()

        tenancy = Tenancy(
            tenant_id=tenant.tenant_id,
            property_id=property.property_id,
            start_date=start_date,
            end_date=end_date,
            monthly_rent=monthly_rent,
            tenancy_status="active"
        )

        db.session.add(tenancy)
        property.availability_status = "occupied"
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Tenancy created successfully.",
            "tenancy": tenancy_response(tenancy)
        }), 201

    except Exception:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Unable to create tenancy."
        }), 500


@tenancies_bp.get("")
@jwt_required()
@role_required("Administrator", "Landlord", "Tenant")
def list_tenancies():
    user = request.current_user
    role = user.role.role_name

    query = Tenancy.query

    if role == "Tenant":
        query = query.join(Tenant).filter(
            Tenant.user_id == user.user_id
        )

    elif role == "Landlord":
        query = query.join(Property).filter(
            Property.owner_id == user.user_id
        )

    tenancies = query.order_by(Tenancy.start_date.desc()).all()

    return jsonify({
        "success": True,
        "count": len(tenancies),
        "tenancies": [
            tenancy_response(tenancy)
            for tenancy in tenancies
        ]
    }), 200


@tenancies_bp.get("/<int:tenancy_id>")
@jwt_required()
@role_required("Administrator", "Landlord", "Tenant")
def get_tenancy(tenancy_id):
    tenancy, error = get_tenancy_access(tenancy_id)

    if error:
        return error

    return jsonify({
        "success": True,
        "tenancy": tenancy_response(tenancy)
    }), 200


@tenancies_bp.patch("/<int:tenancy_id>")
@jwt_required()
@role_required("Administrator", "Landlord")
def update_tenancy(tenancy_id):
    tenancy, error = get_tenancy_access(tenancy_id)

    if error:
        return error

    data = request.get_json(silent=True) or {}

    if "start_date" in data:
        try:
            tenancy.start_date = date.fromisoformat(data["start_date"])
        except (TypeError, ValueError):
            return jsonify({
                "success": False,
                "message": "Invalid start date."
            }), 400

    if "end_date" in data:
        try:
            tenancy.end_date = (
                date.fromisoformat(data["end_date"])
                if data["end_date"] else None
            )
        except (TypeError, ValueError):
            return jsonify({
                "success": False,
                "message": "Invalid end date."
            }), 400

    if tenancy.end_date and tenancy.end_date <= tenancy.start_date:
        return jsonify({
            "success": False,
            "message": "End date must be after start date."
        }), 400

    if "monthly_rent" in data:
        try:
            rent = Decimal(str(data["monthly_rent"]))
            if not rent.is_finite() or rent <= 0:
                raise InvalidOperation
            tenancy.monthly_rent = rent
        except (InvalidOperation, TypeError, ValueError):
            return jsonify({
                "success": False,
                "message": "Monthly rent must be a positive amount."
            }), 400

    if "tenancy_status" in data:
        status = (data.get("tenancy_status") or "").strip().lower()

        if status not in ("active", "completed", "terminated"):
            return jsonify({
                "success": False,
                "message": "Invalid tenancy status."
            }), 400

        if status == "active":
            other_active = Tenancy.query.filter(
                Tenancy.property_id == tenancy.property_id,
                Tenancy.tenancy_status == "active",
                Tenancy.tenancy_id != tenancy.tenancy_id
            ).first()

            if other_active:
                return jsonify({
                    "success": False,
                    "message": "Another active tenancy already exists for this property."
                }), 409

        tenancy.tenancy_status = status

    try:
        active_tenancy = Tenancy.query.filter(
            Tenancy.property_id == tenancy.property_id,
            Tenancy.tenancy_status == "active",
            Tenancy.tenancy_id != tenancy.tenancy_id
        ).first()

        if tenancy.tenancy_status == "active" or active_tenancy:
            tenancy.property.availability_status = "occupied"
        else:
            tenancy.property.availability_status = "available"

        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Tenancy updated successfully.",
            "tenancy": tenancy_response(tenancy)
        }), 200

    except Exception:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Unable to update tenancy."
        }), 500
