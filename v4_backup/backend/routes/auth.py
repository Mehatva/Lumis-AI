from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from models import db
from models.user import User

auth_bp = Blueprint("auth", __name__)

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
    
    db.session.add(user)
    db.session.commit()

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
