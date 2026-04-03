from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
import razorpay
from models import db
from models.business import Business
import os
from utils.auth_utils import business_owned

billing_bp = Blueprint("billing", __name__)

def get_razorpay_client():
    return razorpay.Client(auth=(
        os.environ.get("RAZORPAY_KEY_ID", "rzp_test_mock"), 
        os.environ.get("RAZORPAY_KEY_SECRET", "mock_secret")
    ))

@billing_bp.post("/api/billing/create-order")
@jwt_required()
@business_owned
def create_order(business=None):
    """Create a Razorpay Order for the setup fee + first month."""
    data = request.get_json() or {}
    business_id = data.get("business_id")
    plan_type = data.get("plan_type") # starter, growth, scale
    user_id = get_jwt_identity()

    # The decorator 'business_owned' handles the existence and ownership check

    # Pricing Logic (Prices in Paise for Razorpay)
    # Starter: 1999 setup + 2499 mo = 4498
    # Growth: 4999 setup + 5999 mo = 10998
    # Scale: 9999 setup + 12499 mo = 22498
    pricing = {
        "starter": 4498 * 100,
        "growth": 10998 * 100,
        "scale": 22498 * 100
    }

    amount = pricing.get(plan_type, 4498 * 100)

    try:
        client = get_razorpay_client()
        order_data = {
            "amount": amount,
            "currency": "INR",
            "receipt": f"receipt_biz_{business_id}",
            "notes": {
                "business_id": business_id,
                "plan": plan_type,
                "user_id": user_id
            }
        }
        order = client.order.create(data=order_data)
        
        return jsonify({
            "order_id": order["id"],
            "amount": amount,
            "currency": "INR",
            "key": os.environ.get("RAZORPAY_KEY_ID", "rzp_test_mock")
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@billing_bp.post("/api/billing/webhook")
def razorpay_webhook():
    """Handle Razorpay Webhook for payment verification with strict signature check."""
    webhook_secret = os.environ.get("RAZORPAY_WEBHOOK_SECRET")
    if not webhook_secret:
        print("ERROR: RAZORPAY_WEBHOOK_SECRET not set. Webhook bypassed for security.")
        return jsonify({"status": "error", "message": "Webhook secret missing"}), 500

    payload = request.get_data()
    signature = request.headers.get("X-Razorpay-Signature")

    # Strict Production Verification
    try:
        client = get_razorpay_client()
        client.utility.verify_webhook_signature(payload.decode('utf-8'), signature, webhook_secret)
    except Exception as e:
        print(f"SECURITY WARNING: Invalid Webhook Signature: {e}")
        return jsonify({"status": "unauthorized", "message": "Invalid signature"}), 401

    data = json.loads(payload)
    event = data.get("event")

    if event == "payment.captured":
        payment = data["payload"]["payment"]["entity"]
        order_id = payment["order_id"]
        
        # In a real app, you'd fetch the order to get the notes
        # For simplicity, we'll assume the payment entity has the notes or order has them
        # Let's mock finding the business from order metadata
        notes = payment.get("notes", {})
        business_id = notes.get("business_id")
        plan = notes.get("plan")

        if business_id:
            business = Business.query.get(business_id)
            if business:
                business.plan = plan
                business.is_active = True
                business.razorpay_subscription_id = order_id # Store order_id as ref
                
                # RESET CREDITS & SET LIMITS (Phase 2 Fulfillment)
                business.credits_used = 0
                business.billing_cycle_start = datetime.utcnow()
                
                # Enforce discussed caps
                plan_limits = {
                    "starter": 500,
                    "growth": 2500,
                    "scale": 10000,
                    "pro": 10000
                }
                business.credits_limit = plan_limits.get(plan, 500)
                
                db.session.commit()
                print(f"[RAZORPAY] Fulfillment Success for Business {business_id}: Reset credits to 0, Limit {business.credits_limit}")

    return jsonify({"status": "ok"}), 200
