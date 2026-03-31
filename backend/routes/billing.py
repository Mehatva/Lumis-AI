from flask import Blueprint, request, jsonify, current_app, redirect
import stripe
import os
from models import db
from models.business import Business
from flask_jwt_extended import jwt_required, get_jwt_identity

billing_bp = Blueprint("billing", __name__)

# Initialize Stripe with Secret Key
def get_stripe_key():
    return os.environ.get("STRIPE_SECRET_KEY")

@billing_bp.post("/api/billing/create-checkout-session")
@jwt_required()
def create_checkout_session():
    stripe.api_key = get_stripe_key()
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    plan = data.get("plan", "starter")
    business_id = data.get("business_id")

    if not business_id:
        return jsonify({"error": "Business ID is required"}), 400

    business = Business.query.filter_by(id=business_id, user_id=user_id).first_or_404()

    # Plan details (Mock prices for now)
    prices = {
        "starter": "price_starter_mock", # Replace with real Stripe Price IDs
        "growth": "price_growth_mock",
        "pro": "price_pro_mock"
    }

    # In a real app, you'd use real Stripe Price IDs from your dashboard
    # For this demo/first step, we'll assume a success redirect works
    
    try:
        # Check if customer already exists
        if not business.stripe_customer_id:
            customer = stripe.Customer.create(
                email=business.owner.email,
                metadata={"business_id": business.id}
            )
            business.stripe_customer_id = customer.id
            db.session.commit()

        checkout_session = stripe.checkout.Session.create(
            customer=business.stripe_customer_id,
            line_items=[
                {
                    "price": prices.get(plan, prices["starter"]),
                    "quantity": 1,
                },
            ],
            mode="subscription",
            success_url=f"{request.host_url}dashboard?session_id={{CHECKOUT_SESSION_ID}}&status=success",
            cancel_url=f"{request.host_url}dashboard?status=cancel",
            metadata={
                "business_id": business.id,
                "plan": plan
            }
        )
        return jsonify({"url": checkout_session.url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@billing_bp.post("/api/billing/webhook")
def stripe_webhook():
    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature")
    endpoint_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")

    event = None
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        return "Invalid payload", 400
    except stripe.error.SignatureVerificationError as e:
        return "Invalid signature", 400

    # Handle the event
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        business_id = session.get("metadata", {}).get("business_id")
        plan = session.get("metadata", {}).get("plan")
        
        if business_id and plan:
            business = Business.query.get(business_id)
            if business:
                business.plan = plan
                business.stripe_subscription_id = session.get("subscription")
                db.session.commit()
                print(f"DEBUG: Plan updated for business {business_id} to {plan}")

    return "Success", 200
