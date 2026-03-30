from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from google.oauth2 import id_token
from google.auth.transport import requests
from models import db
from models.user import User
import uuid

auth_bp = Blueprint("auth", __name__)

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

    # MOCK EMAIL: Log verification link to terminal
    print(f"\n[MOCK EMAIL] Verification Link: http://localhost:5001/api/auth/verify-email/{user.verification_token}\n")

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
        return redirect("http://localhost:5001/?error=invalid_token")

    # Mark as verified
    user.is_verified = True
    user.verification_token = None 
    db.session.commit()

    # Redirect to landing page with success flag
    return redirect("http://localhost:5001/?verified=true")

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
