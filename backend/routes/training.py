from flask import Blueprint, jsonify, current_app, request
from models.business import Business
from services.training_service import TrainingService
from models import db
from datetime import datetime

training_bp = Blueprint("training", __name__)

@training_bp.post("/api/business/<int:business_id>/train")
def train_ai(business_id):
    """
    Triggers the TrainingService to synthesize a business profile.
    """
    try:
        # 1. Fetch business
        business = Business.query.get_or_404(business_id)
        
        # 2. Run Training (Uses Groq-Llama3 by default)
        success = TrainingService.train_business(business_id)
        
        if success:
            return jsonify({
                "status": "success",
                "message": "AI successfully trained with new knowledge!",
                "last_trained_at": business.last_trained_at.isoformat() if business.last_trained_at else None,
                "knowledge_summary": business.knowledge_base[:200] + "..." if business.knowledge_base else ""
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to synthesize knowledge. Check logs."
            }), 500

    except Exception as e:
        current_app.logger.error(f"Training API Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@training_bp.get("/api/business/<int:business_id>/status")
def get_training_status(business_id):
    """
    Checks if the business has a knowledge base and when it was last updated.
    """
    business = Business.query.get_or_404(business_id)
    return jsonify({
        "is_trained": bool(business.knowledge_base),
        "last_trained_at": business.last_trained_at.isoformat() if business.last_trained_at else None,
        "hint": "Ready for deployment" if business.knowledge_base else "Training Required"
    }), 200
