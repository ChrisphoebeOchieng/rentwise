from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from app.extensions import db
from app.models import Payment, Tenancy
from app.utils.permissions import role_required


payments_bp = Blueprint(
    "payments",
    __name__,
    url_prefix="/api/payments"
)


def payment_response(payment):
    return {
        "payment_id": payment.payment_id,
        "tenancy_id": payment.tenancy_id,
        "tenant_name": payment.tenancy.tenant.user.full_name,
        "property_name": payment.tenancy.property.property_name,
        "amount_due": str(payment.amount_due),
        "amount_paid": str(payment.amount_paid),
        "balance": str(payment.amount_due - payment.amount_paid),
        "payment_date": (
            payment.payment_date.isoformat()
            if payment.payment_date else None
        ),
        "payment_method": payment.payment_method,
        "transaction_reference": payment.transaction_reference,
        "payment_status": payment.payment_status
    }


def get_payment_access(payment_id):
    payment = db.session.get(Payment, payment_id)

    if not payment:
        return None, (jsonify({
            "success": False,
            "message": "Payment record not found."
        }), 404)

    user = request.current_user
    role = user.role.role_name

    if role == "Administrator":
        return payment, None

    if role == "Tenant" and payment.tenancy.tenant.user_id == user.user_id:
        return payment, None

    if role == "Landlord" and payment.tenancy.property.owner_id == user.user_id:
        return payment, None

    return None, (jsonify({
        "success": False,
        "message": "You do not have permission to access this payment."
    }), 403)


def calculate_status(amount_due, amount_paid):
    if amount_paid == 0:
        return "pending"
    if amount_paid < amount_due:
        return "partial"
    return "paid"


@payments_bp.post("")
@jwt_required()
@role_required("Landlord", "Administrator")
def record_payment():
    data = request.get_json(silent=True) or {}

    try:
        tenancy_id = int(data.get("tenancy_id"))
    except (TypeError, ValueError):
        return jsonify({
            "success": False,
            "message": "A valid tenancy ID is required."
        }), 400

    tenancy = db.session.get(Tenancy, tenancy_id)

    if not tenancy:
        return jsonify({
            "success": False,
            "message": "Tenancy record not found."
        }), 404

    user = request.current_user

    if (
        user.role.role_name == "Landlord"
        and tenancy.property.owner_id != user.user_id
    ):
        return jsonify({
            "success": False,
            "message": "You cannot record payments for another landlord's property."
        }), 403

    if tenancy.tenancy_status != "active":
        return jsonify({
            "success": False,
            "message": "Payments can only be recorded for active tenancies."
        }), 409

    try:
        amount_due = Decimal(str(
            data.get("amount_due", tenancy.monthly_rent)
        ))
        amount_paid = Decimal(str(data.get("amount_paid", 0)))

        if (
            not amount_due.is_finite()
            or not amount_paid.is_finite()
            or amount_due <= 0
            or amount_paid < 0
            or amount_paid > amount_due
        ):
            raise InvalidOperation

    except (InvalidOperation, TypeError, ValueError):
        return jsonify({
            "success": False,
            "message": "Provide valid amounts. Amount due must be positive and amount paid cannot exceed it."
        }), 400

    transaction_reference = (
        (data.get("transaction_reference") or "").strip() or None
    )

    if transaction_reference and Payment.query.filter_by(
        transaction_reference=transaction_reference
    ).first():
        return jsonify({
            "success": False,
            "message": "This transaction reference already exists."
        }), 409

    payment_method = (
        (data.get("payment_method") or "").strip() or None
    )

    payment_date_value = data.get("payment_date")

    try:
        if payment_date_value:
            payment_date = datetime.fromisoformat(
                payment_date_value.replace("Z", "+00:00")
            )
            if payment_date.tzinfo is None:
                payment_date = payment_date.replace(
                    tzinfo=timezone.utc
                )
        else:
            payment_date = datetime.now(timezone.utc)

    except (AttributeError, TypeError, ValueError):
        return jsonify({
            "success": False,
            "message": "Invalid payment date. Use ISO 8601 format."
        }), 400

    payment = Payment(
        tenancy_id=tenancy.tenancy_id,
        amount_due=amount_due,
        amount_paid=amount_paid,
        payment_date=payment_date,
        payment_method=payment_method,
        transaction_reference=transaction_reference,
        payment_status=calculate_status(amount_due, amount_paid)
    )

    try:
        db.session.add(payment)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Payment recorded successfully.",
            "payment": payment_response(payment)
        }), 201

    except Exception:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Unable to record payment."
        }), 500


@payments_bp.get("")
@jwt_required()
@role_required("Administrator", "Landlord", "Tenant")
def list_payments():
    user = request.current_user
    role = user.role.role_name

    query = Payment.query.join(Tenancy)

    if role == "Tenant":
        query = query.filter(
            Tenancy.tenant.has(user_id=user.user_id)
        )

    elif role == "Landlord":
        query = query.filter(
            Tenancy.property.has(owner_id=user.user_id)
        )

    payments = query.order_by(
        Payment.payment_date.desc()
    ).all()

    return jsonify({
        "success": True,
        "count": len(payments),
        "payments": [
            payment_response(payment)
            for payment in payments
        ]
    }), 200


@payments_bp.get("/<int:payment_id>")
@jwt_required()
@role_required("Administrator", "Landlord", "Tenant")
def get_payment(payment_id):
    payment, error = get_payment_access(payment_id)

    if error:
        return error

    return jsonify({
        "success": True,
        "payment": payment_response(payment)
    }), 200


@payments_bp.patch("/<int:payment_id>")
@jwt_required()
@role_required("Landlord", "Administrator")
def update_payment(payment_id):
    payment, error = get_payment_access(payment_id)

    if error:
        return error

    data = request.get_json(silent=True) or {}

    if "amount_due" in data or "amount_paid" in data:
        try:
            amount_due = Decimal(str(
                data.get("amount_due", payment.amount_due)
            ))
            amount_paid = Decimal(str(
                data.get("amount_paid", payment.amount_paid)
            ))

            if (
                not amount_due.is_finite()
                or not amount_paid.is_finite()
                or amount_due <= 0
                or amount_paid < 0
                or amount_paid > amount_due
            ):
                raise InvalidOperation

        except (InvalidOperation, TypeError, ValueError):
            return jsonify({
                "success": False,
                "message": "Invalid payment amounts."
            }), 400

        payment.amount_due = amount_due
        payment.amount_paid = amount_paid
        payment.payment_status = calculate_status(
            amount_due, amount_paid
        )

    if "payment_method" in data:
        payment.payment_method = (
            (data.get("payment_method") or "").strip() or None
        )

    if "transaction_reference" in data:
        reference = (
            (data.get("transaction_reference") or "").strip() or None
        )

        if reference and Payment.query.filter(
            Payment.transaction_reference == reference,
            Payment.payment_id != payment.payment_id
        ).first():
            return jsonify({
                "success": False,
                "message": "This transaction reference already exists."
            }), 409

        payment.transaction_reference = reference

    if "payment_date" in data:
        try:
            payment_date = datetime.fromisoformat(
                data["payment_date"].replace("Z", "+00:00")
            )
            if payment_date.tzinfo is None:
                payment_date = payment_date.replace(
                    tzinfo=timezone.utc
                )
            payment.payment_date = payment_date
        except (AttributeError, TypeError, ValueError):
            return jsonify({
                "success": False,
                "message": "Invalid payment date."
            }), 400

    try:
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Payment updated successfully.",
            "payment": payment_response(payment)
        }), 200

    except Exception:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Unable to update payment."
        }), 500
