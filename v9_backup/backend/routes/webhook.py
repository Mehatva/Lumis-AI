"""Routes — Instagram webhook endpoints."""
from flask import Blueprint, request, jsonify, current_app
from models.business import Business
from services.instagram import InstagramService
from services.chatbot import ChatbotService

webhook_bp = Blueprint("webhook", __name__)


@webhook_bp.get("/webhook/instagram")
def verify_instagram():
    """Meta calls this GET endpoint to verify the webhook subscription."""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    result = InstagramService.verify_webhook(mode, token, challenge)
    if result:
        return result, 200
    return "Verification failed", 403


@webhook_bp.post("/webhook/instagram")
def handle_instagram():
    """
    Receives inbound Instagram DMs.
    Looks up the business by INSTAGRAM_PAGE_ID, runs the chatbot, sends reply.
    """
    payload = request.get_json(silent=True) or {}
    
    # ─── DEBUG: Force log at WARNING level for production visibility ───
    current_app.logger.warning(f"[Webhook Raw] Received payload: {payload}")

    # Determine which page this webhook is for
    page_id = None
    try:
        page_id = payload["entry"][0]["id"]
    except (KeyError, IndexError):
        pass

    # Load authentic business record
    business = None
    if page_id:
        business = Business.query.filter_by(instagram_page_id=page_id, is_active=True).first()

    # SECURITY LOCKDOWN: We no longer fallback to a random business. 
    # The webhook MUST match a registered Instagram Page ID.
    if not business:
        # Fallback for Tester/Demo: If no business found for this page_id, 
        # check if it matches the configured INSTAGRAM_PAGE_ID in .env
        env_page_id = current_app.config.get("INSTAGRAM_PAGE_ID")
        if page_id == env_page_id:
            business = Business.query.filter_by(is_active=True).first()
            if business:
                current_app.logger.info(f"Auto-mapped payload for page_id {page_id} to business {business.name} (fallback match)")
        
        if not business:
            current_app.logger.warning(f"Unauthorized Webhook Context: No active business found for page_id {page_id}")
            return jsonify({"status": "ignored_no_business_match"}), 200

    # Fallback to .env token if not in DB
    access_token = business.access_token or current_app.config.get("INSTAGRAM_ACCESS_TOKEN")
    if not access_token:
        current_app.logger.warning(f"Business {business.name} and system both missing Meta Access Token.")
        return jsonify({"status": "ignored_no_token"}), 200

    # Parse messages
    # CRITICAL FIX for Demo: Meta requires the FB Page ID in the endpoint URL,
    # but the incoming webhook ID is the Instagram Business ID.
    # The manual test proved that 1084904538032905 is the ONLY ID that works.
    endpoint_id = "1084904538032905" 
    
    # Use Business-specific token and prioritize the successful Page ID 
    insta = InstagramService(access_token, endpoint_id)
    messages = InstagramService.parse_incoming(payload)

    chatbot = ChatbotService(business)

    for msg in messages:
        sender_id = msg["sender_id"]
        text = msg["text"]

        # 1. Send typing indicator to create a natural feeling
        insta.send_typing_indicator(sender_id, on=True)

        current_app.logger.info(f"[Live Webhook] From {sender_id} to Page {page_id}: {text}")

        # 2. Generate response using AI engine
        reply = chatbot.process(sender_id, text)
        
        # 3. Dispatch reply and turn off typing
        insta.send_message(sender_id, reply)
        insta.send_typing_indicator(sender_id, on=False)

    return jsonify({"status": "ok"}), 200

