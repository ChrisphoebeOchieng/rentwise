from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import func
from app.extensions import db
from app.models import (
    Property,
    RentalApplication,
    Tenancy,
    Payment,
    MaintenanceRequest
)
from app.utils.permissions import role_required

reports_bp = Blueprint("reports", __name__, url_prefix="/api/reports")


def report_scope():
    user = request.current_user

    properties = Property.query

    if user.role.role_name == "Landlord":
        properties = properties.filter_by(owner_id=user.user_id)

    return properties


def property_ids():
    return [p.property_id for p in report_scope().all()]


def money(value):
    return float(value or 0)


@reports_bp.route("/dashboard", methods=["GET"])
@jwt_required()
@role_required("Administrator", "Landlord")
def dashboard_report():
    ids = property_ids()

    total_properties = len(ids)

    occupied = Property.query.filter(
        Property.property_id.in_(ids),
        Property.availability_status == "occupied"
    ).count() if ids else 0

    active_tenancies = Tenancy.query.filter(
        Tenancy.property_id.in_(ids),
        Tenancy.tenancy_status == "active"
    ).count() if ids else 0

    application_stats = {}
    if ids:
        results = db.session.query(
            RentalApplication.application_status,
            func.count(RentalApplication.application_id)
        ).filter(
            RentalApplication.property_id.in_(ids)
        ).group_by(
            RentalApplication.application_status
        ).all()

        application_stats = {
            status: count for status, count in results
        }

    occupancy_rate = (
        round((occupied / total_properties) * 100, 2)
        if total_properties else 0
    )

    return jsonify({
        "success": True,
        "dashboard": {
            "total_properties": total_properties,
            "occupied_properties": occupied,
            "available_properties": max(total_properties - occupied, 0),
            "occupancy_rate": occupancy_rate,
            "active_tenancies": active_tenancies,
            "total_applications": sum(application_stats.values()),
            "application_statistics": application_stats
        }
    }), 200


@reports_bp.route("/financial", methods=["GET"])
@jwt_required()
@role_required("Administrator", "Landlord")
def financial_report():
    ids = property_ids()

    payments = db.session.query(
        func.coalesce(func.sum(Payment.amount_due), 0),
        func.coalesce(func.sum(Payment.amount_paid), 0)
    ).join(
        Tenancy, Payment.tenancy_id == Tenancy.tenancy_id
    ).filter(
        Tenancy.property_id.in_(ids)
    ).first() if ids else (0, 0)

    total_due = money(payments[0])
    total_collected = money(payments[1])
    outstanding = max(total_due - total_collected, 0)

    payment_stats = {}
    if ids:
        results = db.session.query(
            Payment.payment_status,
            func.count(Payment.payment_id)
        ).join(
            Tenancy, Payment.tenancy_id == Tenancy.tenancy_id
        ).filter(
            Tenancy.property_id.in_(ids)
        ).group_by(
            Payment.payment_status
        ).all()

        payment_stats = {
            status: count for status, count in results
        }

    return jsonify({
        "success": True,
        "financial_report": {
            "total_amount_due": total_due,
            "total_amount_collected": total_collected,
            "outstanding_balance": outstanding,
            "payment_statistics": payment_stats
        }
    }), 200


@reports_bp.route("/operations", methods=["GET"])
@jwt_required()
@role_required("Administrator", "Landlord")
def operations_report():
    ids = property_ids()

    maintenance_stats = {}
    priority_stats = {}

    if ids:
        status_results = db.session.query(
            MaintenanceRequest.request_status,
            func.count(MaintenanceRequest.request_id)
        ).filter(
            MaintenanceRequest.property_id.in_(ids)
        ).group_by(
            MaintenanceRequest.request_status
        ).all()

        priority_results = db.session.query(
            MaintenanceRequest.priority,
            func.count(MaintenanceRequest.request_id)
        ).filter(
            MaintenanceRequest.property_id.in_(ids)
        ).group_by(
            MaintenanceRequest.priority
        ).all()

        maintenance_stats = {
            status: count for status, count in status_results
        }

        priority_stats = {
            priority: count for priority, count in priority_results
        }

    total_requests = sum(maintenance_stats.values())

    return jsonify({
        "success": True,
        "operations_report": {
            "total_maintenance_requests": total_requests,
            "maintenance_by_status": maintenance_stats,
            "maintenance_by_priority": priority_stats
        }
    }), 200
