from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from app.extensions import db
from app.models import MaintenanceRequest, Property, Tenant, Tenancy
from app.utils.permissions import role_required


maintenance_bp = Blueprint("maintenance", __name__, url_prefix="/api/maintenance")


def maintenance_response(maintenance):
    return {
        "request_id": maintenance.request_id,
        "property_id": maintenance.property_id,
        "property_name": maintenance.property.property_name,
        "tenant_id": maintenance.tenant_id,
        "tenant_name": maintenance.tenant.user.full_name,
        "description": maintenance.description,
        "request_date": (
            maintenance.request_date.isoformat()
            if maintenance.request_date else None
        ),
        "priority": maintenance.priority,
        "request_status": maintenance.request_status,
        "resolution_details": maintenance.resolution_details,
    }


def can_access_request(user, maintenance):
    if user.role.role_name == "Administrator":
        return True

    if user.role.role_name == "Landlord":
        return maintenance.property.owner_id == user.user_id

    if user.role.role_name == "Tenant":
        return maintenance.tenant.user_id == user.user_id

    return False


@maintenance_bp.route("", methods=["POST"])
@jwt_required()
@role_required("Tenant")
def create_maintenance_request():
    user = request.current_user
    data = request.get_json(silent=True) or {}

    property_id = data.get("property_id")
    description = data.get("description")

    if not property_id or not isinstance(description, str) or not description.strip():
        return jsonify({
            "success": False,
            "message": "Property ID and description are required."
        }), 400

    try:
        property_id = int(property_id)
    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "message": "Property ID must be a valid integer."
        }), 400

    tenant = Tenant.query.filter_by(user_id=user.user_id).first()

    if not tenant:
        return jsonify({
            "success": False,
            "message": "Tenant profile not found."
        }), 404

    active_tenancy = Tenancy.query.filter_by(
        tenant_id=tenant.tenant_id,
        property_id=property_id,
        tenancy_status="active"
    ).first()

    if not active_tenancy:
        return jsonify({
            "success": False,
            "message": "You can only submit maintenance requests for properties where you have an active tenancy."
        }), 403

    priority = str(data.get("priority", "normal")).lower()

    if priority not in ["low", "normal", "high", "urgent"]:
        return jsonify({
            "success": False,
            "message": "Priority must be low, normal, high, or urgent."
        }), 400

    maintenance = MaintenanceRequest(
        property_id=property_id,
        tenant_id=tenant.tenant_id,
        description=description.strip(),
        priority=priority,
        request_status="pending"
    )

    db.session.add(maintenance)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Maintenance request submitted successfully.",
        "maintenance_request": maintenance_response(maintenance)
    }), 201


@maintenance_bp.route("", methods=["GET"])
@jwt_required()
@role_required("Administrator", "Landlord", "Tenant")
def list_maintenance_requests():
    user = request.current_user

    query = MaintenanceRequest.query

    if user.role.role_name == "Landlord":
        query = query.join(Property).filter(
            Property.owner_id == user.user_id
        )

    elif user.role.role_name == "Tenant":
        tenant = Tenant.query.filter_by(user_id=user.user_id).first()

        if not tenant:
            return jsonify({
                "success": True,
                "count": 0,
                "maintenance_requests": []
            }), 200

        query = query.filter_by(tenant_id=tenant.tenant_id)

    requests_list = query.order_by(
        MaintenanceRequest.request_date.desc()
    ).all()

    return jsonify({
        "success": True,
        "count": len(requests_list),
        "maintenance_requests": [
            maintenance_response(item) for item in requests_list
        ]
    }), 200


@maintenance_bp.route("/<int:request_id>", methods=["GET"])
@jwt_required()
@role_required("Administrator", "Landlord", "Tenant")
def get_maintenance_request(request_id):
    user = request.current_user

    maintenance = db.session.get(MaintenanceRequest, request_id)

    if not maintenance:
        return jsonify({
            "success": False,
            "message": "Maintenance request not found."
        }), 404

    if not can_access_request(user, maintenance):
        return jsonify({
            "success": False,
            "message": "You do not have permission to view this maintenance request."
        }), 403

    return jsonify({
        "success": True,
        "maintenance_request": maintenance_response(maintenance)
    }), 200


@maintenance_bp.route("/<int:request_id>", methods=["PATCH"])
@jwt_required()
@role_required("Administrator", "Landlord")
def update_maintenance_request(request_id):
    user = request.current_user
    data = request.get_json(silent=True) or {}

    maintenance = db.session.get(MaintenanceRequest, request_id)

    if not maintenance:
        return jsonify({
            "success": False,
            "message": "Maintenance request not found."
        }), 404

    if not can_access_request(user, maintenance):
        return jsonify({
            "success": False,
            "message": "You do not have permission to update this maintenance request."
        }), 403

    allowed_fields = {"priority", "request_status", "resolution_details"}

    if not data or not set(data.keys()).issubset(allowed_fields):
        return jsonify({
            "success": False,
            "message": "Provide valid maintenance request fields to update."
        }), 400

    if "priority" in data:
        priority = str(data["priority"]).lower()

        if priority not in ["low", "normal", "high", "urgent"]:
            return jsonify({
                "success": False,
                "message": "Priority must be low, normal, high, or urgent."
            }), 400

        maintenance.priority = priority

    if "request_status" in data:
        status = str(data["request_status"]).lower()

        if status not in ["pending", "in_progress", "resolved", "rejected"]:
            return jsonify({
                "success": False,
                "message": "Status must be pending, in_progress, resolved, or rejected."
            }), 400

        maintenance.request_status = status

    if "resolution_details" in data:
        details = data["resolution_details"]

        if details is not None and not isinstance(details, str):
            return jsonify({
                "success": False,
                "message": "Resolution details must be text."
            }), 400

        maintenance.resolution_details = details.strip() if details else None

    if maintenance.request_status == "resolved" and not maintenance.resolution_details:
        return jsonify({
            "success": False,
            "message": "Resolution details are required when resolving a request."
        }), 400

    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Maintenance request updated successfully.",
        "maintenance_request": maintenance_response(maintenance)
    }), 200
