from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from app.extensions import db
from app.models import Property
from app.utils.permissions import role_required


properties_bp = Blueprint(
    "properties",
    __name__,
    url_prefix="/api/properties"
)


def property_response(property):
    return {
        "property_id": property.property_id,
        "owner_id": property.owner_id,
        "property_name": property.property_name,
        "property_type": property.property_type,
        "location": property.location,
        "description": property.description,
        "monthly_rent": str(property.monthly_rent),
        "availability_status": property.availability_status,
        "created_at": (
            property.created_at.isoformat()
            if property.created_at else None
        )
    }


def get_property_access(property_id):
    property = db.session.get(Property, property_id)

    if not property:
        return None, (jsonify({
            "success": False,
            "message": "Property not found."
        }), 404)

    user = request.current_user
    role = user.role.role_name

    if role == "Administrator":
        return property, None

    if role == "Landlord" and property.owner_id == user.user_id:
        return property, None

    if role == "Tenant" and property.availability_status == "available":
        return property, None

    return None, (jsonify({
        "success": False,
        "message": "You do not have permission to access this property."
    }), 403)


@properties_bp.post("")
@jwt_required()
@role_required("Administrator", "Landlord")
def create_property():
    data = request.get_json(silent=True) or {}

    property_name = (data.get("property_name") or "").strip()
    property_type = (data.get("property_type") or "").strip()
    location = (data.get("location") or "").strip()
    description = (data.get("description") or "").strip() or None
    monthly_rent = data.get("monthly_rent")

    if not property_name or not property_type or not location:
        return jsonify({
            "success": False,
            "message": "Property name, type and location are required."
        }), 400

    try:
        monthly_rent = Decimal(str(monthly_rent))
        if not monthly_rent.is_finite() or monthly_rent <= 0:
            raise InvalidOperation
    except (InvalidOperation, TypeError, ValueError):
        return jsonify({
            "success": False,
            "message": "Monthly rent must be a valid positive amount."
        }), 400

    availability_status = (
        data.get("availability_status") or "available"
    ).strip().lower()

    if availability_status not in ("available", "occupied", "unavailable"):
        return jsonify({
            "success": False,
            "message": "Invalid property availability status."
        }), 400

    user = request.current_user

    property = Property(
        owner_id=user.user_id,
        property_name=property_name,
        property_type=property_type,
        location=location,
        description=description,
        monthly_rent=monthly_rent,
        availability_status=availability_status
    )

    try:
        db.session.add(property)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Property created successfully.",
            "property": property_response(property)
        }), 201

    except Exception:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Unable to create property."
        }), 500


@properties_bp.get("")
@jwt_required()
@role_required(
    "Administrator",
    "Landlord",
    "Tenant"
)
def list_properties():
    user = request.current_user
    role = user.role.role_name

    query = Property.query

    if role == "Landlord":
        query = query.filter_by(owner_id=user.user_id)

    elif role == "Tenant":
        query = query.filter_by(availability_status="available")

    properties = query.order_by(Property.created_at.desc()).all()

    return jsonify({
        "success": True,
        "count": len(properties),
        "properties": [
            property_response(property)
            for property in properties
        ]
    }), 200


@properties_bp.get("/<int:property_id>")
@jwt_required()
@role_required(
    "Administrator",
    "Landlord",
    "Tenant"
)
def get_property(property_id):
    property, error = get_property_access(property_id)

    if error:
        return error

    return jsonify({
        "success": True,
        "property": property_response(property)
    }), 200


@properties_bp.put("/<int:property_id>")
@jwt_required()
@role_required("Administrator", "Landlord")
def update_property(property_id):
    property, error = get_property_access(property_id)

    if error:
        return error

    data = request.get_json(silent=True) or {}

    if "property_name" in data:
        property_name = (data.get("property_name") or "").strip()
        if not property_name:
            return jsonify({
                "success": False,
                "message": "Property name cannot be empty."
            }), 400
        property.property_name = property_name

    if "property_type" in data:
        property_type = (data.get("property_type") or "").strip()
        if not property_type:
            return jsonify({
                "success": False,
                "message": "Property type cannot be empty."
            }), 400
        property.property_type = property_type

    if "location" in data:
        location = (data.get("location") or "").strip()
        if not location:
            return jsonify({
                "success": False,
                "message": "Property location cannot be empty."
            }), 400
        property.location = location

    if "description" in data:
        property.description = (
            (data.get("description") or "").strip() or None
        )

    if "monthly_rent" in data:
        try:
            monthly_rent = Decimal(str(data["monthly_rent"]))
            if not monthly_rent.is_finite() or monthly_rent <= 0:
                raise InvalidOperation
            property.monthly_rent = monthly_rent
        except (InvalidOperation, TypeError, ValueError):
            return jsonify({
                "success": False,
                "message": "Monthly rent must be a valid positive amount."
            }), 400

    if "availability_status" in data:
        status = (data.get("availability_status") or "").strip().lower()

        if status not in ("available", "occupied", "unavailable"):
            return jsonify({
                "success": False,
                "message": "Invalid property availability status."
            }), 400

        property.availability_status = status

    try:
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Property updated successfully.",
            "property": property_response(property)
        }), 200

    except Exception:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Unable to update property."
        }), 500


@properties_bp.delete("/<int:property_id>")
@jwt_required()
@role_required("Administrator", "Landlord")
def delete_property(property_id):
    property, error = get_property_access(property_id)

    if error:
        return error

    if (
        property.applications
        or property.tenancies
        or property.maintenance_requests
    ):
        return jsonify({
            "success": False,
            "message": (
                "This property has related rental records and cannot "
                "be deleted. Update its availability status instead."
            )
        }), 409

    try:
        db.session.delete(property)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Property deleted successfully."
        }), 200

    except Exception:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Unable to delete property."
        }), 500
