from flask import Blueprint, request, jsonify, current_app, redirect
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from google.oauth2 import id_token
from google.auth.transport import requests
from models import db
from models.user import User
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

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid email or password"}), 401

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
