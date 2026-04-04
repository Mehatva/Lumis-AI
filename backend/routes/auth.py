from flask import Blueprint, request, jsonify, current_app, redirect
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from google.oauth2 import id_token
from google.auth.transport import requests
from models import db
from models.user import User
from models.business import Business
from services.instagram import InstagramService
import uuid
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import threading

auth_bp = Blueprint("auth", __name__)

def send_verification_email_async(to_email, verification_link):
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    smtp_username = os.environ.get("SMTP_USERNAME")
    smtp_password = os.environ.get("SMTP_PASSWORD")

    if not smtp_username or not smtp_password:
        print(f"\n[MOCK EMAIL - NO SMTP CONFIGURED] Verification Link: {verification_link}\n")
        return

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Welcome to Lumis AI — Action Required"
        msg["From"] = f"Lumis AI <{smtp_username}>"
        msg["To"] = to_email

        html_content = f"""
        <html>
          <body style="font-family: Arial, sans-serif; background-color: #020406; color: #ffffff; padding: 40px 20px;">
            <div style="max-width: 600px; margin: 0 auto; background: #06060a; padding: 40px; border-radius: 12px; border: 1px solid #14b8a6; text-align: center;">
              <h2 style="color: #ffffff; margin-bottom: 10px;">Welcome to <span style="color: #14b8a6;">Lumis AI</span></h2>
              <p style="color: #a0aec0; font-size: 16px; line-height: 1.6; margin-bottom: 30px;">
                You're almost there! We just need to verify your email address to secure your account and grant you full access to the platform.
              </p>
              <a href="{verification_link}" style="display: inline-block; padding: 14px 28px; background-color: #14b8a6; color: #ffffff; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 16px;">Verify My Email</a>
              <p style="color: #4a5568; font-size: 12px; margin-top: 40px;">If you didn't create an account, you can safely ignore this email.</p>
            </div>
          </body>
        </html>
        """
        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
            print(f"[SMTP] Successfully sent verification email to {to_email}")
    except Exception as e:
        print(f"[SMTP ERROR] Failed to send email to {to_email}: {e}")

@auth_bp.get("/api/auth/config")
def get_auth_config():
    return jsonify({
        "google_client_id": current_app.config.get("GOOGLE_CLIENT_ID")
    }), 200

@auth_bp.post("/api/auth/signup")
def signup():
    data = request.get_json() or {}
    email = data.get("email")
    password = data.get("password")
    name = data.get("name")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    email = email.lower().strip()

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 400

    user = User(email=email, name=name)
    user.set_password(password)
    
    # Generate verification token
    user.verification_token = str(uuid.uuid4())
    
    db.session.add(user)
    db.session.commit()

    # Dispatch email asynchronously so it doesn't block the UI
    base_url = current_app.config.get("BASE_URL", "http://localhost:5001")
    verification_link = f"{base_url}/api/auth/verify-email/{user.verification_token}"
    threading.Thread(target=send_verification_email_async, args=(email, verification_link)).start()

    access_token = create_access_token(identity=str(user.id))
    return jsonify({
        "message": "User created successfully",
        "access_token": access_token,
        "user": user.to_dict()
    }), 201

@auth_bp.post("/api/auth/login")
def login():
    data = request.get_json() or {}
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    email = email.lower().strip()

    print(f"[DEBUG LOGIN] Attempt: {email}")

    user = User.query.filter_by(email=email).first()
    if not user:
        print(f"[DEBUG LOGIN] User {email} not found in DB.")
        return jsonify({"error": "Invalid email or password"}), 401

    if not user.check_password(password):
        print(f"[DEBUG LOGIN] Password mismatch for {email}.")
        print(f"[DEBUG LOGIN] User hash: {user.password_hash[:10]}...")
        return jsonify({"error": "Invalid email or password"}), 401

    print(f"[DEBUG LOGIN] Successful login: {email}")

    access_token = create_access_token(identity=str(user.id))
    return jsonify({
        "access_token": access_token,
        "user": user.to_dict()
    }), 200

@auth_bp.get("/api/auth/me")
@jwt_required()
def me():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user.to_dict()), 200

@auth_bp.post("/api/auth/google")
def google_login():
    data = request.get_json() or {}
    token = data.get("credential") # The ID token from Google

    if not token:
        return jsonify({"error": "Google token is required"}), 400

    try:
        # Verify the ID token
        id_info = id_token.verify_oauth2_token(
            token, 
            requests.Request(), 
            current_app.config["GOOGLE_CLIENT_ID"]
        )

        # ID token is valid. Get the user's profile information from the decoded token.
        email = id_info.get("email")
        name = id_info.get("name")
        google_id = id_info.get("sub")

        if not email:
            return jsonify({"error": "Email not found in Google token"}), 400

        email = email.lower().strip()

        # Check if user exists
        user = User.query.filter_by(email=email).first()

        if not user:
            # Create new user
            user = User(email=email, name=name, is_verified=True)
            # For Google users, we might not have a password, so we set a random or empty one
            # and rely on Google for future logins.
            user.set_password(f"google_{google_id}") 
            db.session.add(user)
            db.session.commit()

        # Create access token
        access_token = create_access_token(identity=str(user.id))
        
        return jsonify({
            "message": "Google login successful",
            "access_token": access_token,
            "user": user.to_dict()
        }), 200

    except ValueError as e:
        # Invalid token
        return jsonify({"error": f"Invalid Google token: {str(e)}"}), 401
    except Exception as e:
        return jsonify({"error": f"Authentication failed: {str(e)}"}), 500
@auth_bp.get("/api/auth/verify-email/<token>")
def verify_email(token):
    user = User.query.filter_by(verification_token=token).first()
    if not user:
        # If token is not found, check if it's already verified or just invalid
        base_url = current_app.config.get("BASE_URL", "http://localhost:5001")
        return redirect(f"{base_url}/?error=invalid_token")

    # Mark as verified
    user.is_verified = True
    user.verification_token = None 
    db.session.commit()

    # Redirect to landing page with success flag
    base_url = current_app.config.get("BASE_URL", "http://localhost:5001")
    return redirect(f"{base_url}/?verified=true")

@auth_bp.post("/api/auth/apple")
def apple_login():
    # Placeholder for Apple Sign-in verification
    # Requires client_id, team_id, key_id, and .p8 private key
    return jsonify({"error": "Apple Sign-in is not yet configured. Please provide your Apple Developer credentials."}), 501

@auth_bp.post("/api/auth/instagram")
def instagram_login():
    # Placeholder for Instagram Sign-in 
    # Requires Meta App ID and Client Secret
    return jsonify({"error": "Instagram Sign-in is not yet configured. Please provide your Meta App Developer credentials."}), 501


@auth_bp.get("/api/auth/instagram/init")
@jwt_required()
def instagram_init():
    """
    Returns the Meta authorization URL.
    """
    business_id = request.args.get("business_id")
    if not business_id:
        return jsonify({"error": "business_id is required"}), 400
        
    try:
        base_url = current_app.config.get("BASE_URL", "http://localhost:5001")
        redirect_uri = f"{base_url}/api/auth/instagram/callback"
        auth_url = InstagramService.get_auth_url(redirect_uri)
        
        # Store business_id in 'state' to retrieve it during callback
        auth_url += f"&state={business_id}"
        
        return jsonify({"auth_url": auth_url}), 200
    except ValueError as e:
        current_app.logger.error(f"Instagram Init Error: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Instagram Init Failed: {e}")
        return jsonify({"error": "Failed to initialize Instagram connection. Please check server logs."}), 500


@auth_bp.get("/api/auth/instagram/callback")
def instagram_callback():
    """
    Handles the Meta OAuth redirect.
    """
    code = request.args.get("code")
    business_id = request.args.get("state")
    error = request.args.get("error")
    
    base_url = current_app.config.get("BASE_URL", "http://localhost:5001")

    if error:
        return redirect(f"{base_url}/dashboard?instagram_error={error}")
        
    if not code or not business_id:
        return redirect(f"{base_url}/dashboard?instagram_error=missing_params")

    try:
        redirect_uri = f"{base_url}/api/auth/instagram/callback"
        
        # 1. Exchange code for short-lived user token
        token_data = InstagramService.exchange_code_for_token(code, redirect_uri)
        if "error" in token_data:
            print(f"[OAuth Callback] Token exchange failed: {token_data}")
            return redirect(f"{base_url}/dashboard?instagram_error=token_exchange_failed")
            
        short_token = token_data.get("access_token")
        
        # 2. Get long-lived user token
        long_token = InstagramService.get_long_lived_token(short_token)
        if not long_token:
            long_token = short_token

        # 3. Get managed pages for this user
        pages = InstagramService.get_managed_pages(long_token)
        current_app.logger.info(f"[OAuth Callback] Pages found: {len(pages) if pages else 0}")
        
        if not pages:
            current_app.logger.warning("[OAuth Callback] No pages returned from Meta accounts API")
            return redirect(f"{base_url}/dashboard?instagram_error=no_pages_found")
            
        # Identify the first page with a linked Instagram account
        selected_page_id = None
        ig_business_id = None
        page_access_token = None
        
        for page in pages:
            p_id = page.get("id")
            p_token = page.get("access_token")
            ig_id = InstagramService.get_ig_account_for_page(p_id, p_token)
            if ig_id:
                selected_page_id = p_id
                ig_business_id = ig_id
                page_access_token = p_token
                break
                
        if not ig_business_id:
            return redirect(f"{base_url}/dashboard?instagram_error=no_ig_account_linked")

        # 4. Update the business profile
        business = Business.query.get(business_id)
        if not business:
            return redirect(f"{base_url}/dashboard?instagram_error=business_not_found")
            
        # 4b. Fetch IG account details (username)
        ig_details = InstagramService.get_ig_account_details(ig_business_id, page_access_token)
        if ig_details and "username" in ig_details:
            business.instagram_handle = f"@{ig_details['username']}"
            
        business.instagram_page_id = ig_business_id
        business.access_token = page_access_token
        business.instagram_user_token = long_token
        business.token_updated_at = datetime.utcnow()
        db.session.commit()
        
        # 5. AUTO-SUBSCRIBE
        InstagramService.subscribe_app_to_page(ig_business_id, page_access_token)

        return redirect(f"{base_url}/dashboard?instagram_success=true")

    except Exception as e:
        print(f"[OAuth Callback] Error: {e}")
        return redirect(f"{base_url}/dashboard?instagram_error=server_error")

# ═══════════════════════════════════════════════════════════════════════
# META COMPLIANCE: DATA DELETION CALLBACK
# ═══════════════════════════════════════════════════════════════════════
from services.compliance_service import ComplianceService

@auth_bp.route("/api/auth/data-deletion", methods=["POST"])
def data_deletion():
    """
    Data Deletion Callback for Meta Apps.
    Meta sends a POST with signed_request when a user removes the app.
    """
    try:
        signed_request = request.form.get("signed_request")
        if not signed_request:
            return jsonify({"error": "Missing signed_request"}), 400

        data = ComplianceService.parse_signed_request(signed_request)
        if not data:
            return jsonify({"error": "Invalid signature"}), 400

        user_id = data.get("user_id")
        result = ComplianceService.handle_data_deletion(user_id)
        
        return jsonify(result), 200

    except Exception as e:
        current_app.logger.error(f"Data deletion callback failed: {e}")
        return jsonify({"error": "Server error"}), 500

@auth_bp.route("/api/auth/deletion-status/<confirmation_code>", methods=["GET"])
def deletion_status(confirmation_code):
    """
    Public deletion status page for user confirmation.
    """
    # Simple HTML response for user transparency
    return f"""
    <html>
        <head><title>Deletion Status - Lumis AI</title></head>
        <body style="background: #050505; color: #fff; display: flex; justify-content: center; align-items: center; height: 100vh; font-family: sans-serif;">
            <div style="background: rgba(255,255,255,0.05); padding: 40px; border-radius: 20px; border: 1px solid rgba(255,255,255,0.1); max-width: 500px; text-align: center;">
                <h1 style="color: #6366f1;">Request Confirmed</h1>
                <p style="color: rgba(255,255,255,0.7);">Your data deletion request (<b>{confirmation_code}</b>) has been received and processed.</p>
                <p style="font-size: 0.9rem; color: #666; margin-top: 20px;">All associated Meta Access Tokens and Business Intelligence have been purged.</p>
                <a href="/" style="color: #6366f1; text-decoration: none; margin-top: 20px; display: inline-block;">Return to Lumis AI</a>
            </div>
        </body>
    </html>
    """, 200
