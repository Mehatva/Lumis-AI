from functools import wraps
from flask import jsonify, abort
from flask_jwt_extended import get_jwt_identity
from models.business import Business
from models.faq import FAQ
from models.lead import Lead

def business_owned(f):
    """
    Decorator to ensure the current JWT user owns the business.
    Works for routes with <int:business_id> in the URL or business_id in JSON body.
    Returns 404 if not owned to prevent ID fishing.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import request
        user_id = get_jwt_identity()
        business_id = kwargs.get("business_id")
        
        if not business_id:
            # Check JSON body
            data = request.get_json(silent=True) or {}
            business_id = data.get("business_id")
            
        if not business_id:
            abort(400, description="Missing business_id")
            
        business = Business.query.filter_by(id=business_id, user_id=user_id).first()
        if not business:
            # Return 404 to avoid leaking that the business exists (more secure than 403)
            abort(404, description="Resource not found or unauthorized access.")
            
        # Inject the business object into the function as an optional keyword argument
        kwargs["business"] = business
        return f(*args, **kwargs)
        
    return decorated_function

def faq_owned(f):
    """
    Decorator to ensure the current JWT user owns the business parent of an FAQ.
    Works for routes with <int:faq_id> in the URL.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = get_jwt_identity()
        faq_id = kwargs.get("faq_id")
        
        faq = FAQ.query.get_or_404(faq_id)
        business = Business.query.filter_by(id=faq.business_id, user_id=user_id).first()
        if not business:
            abort(404, description="Resource not found or unauthorized access.")
            
        kwargs["faq"] = faq
        kwargs["business"] = business
        return f(*args, **kwargs)
        
    return decorated_function

def lead_owned(f):
    """
    Decorator to ensure the current JWT user owns the business parent of a Lead.
    Works for routes with <int:lead_id> in the URL.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = get_jwt_identity()
        lead_id = kwargs.get("lead_id")
        
        lead = Lead.query.get_or_404(lead_id)
        business = Business.query.filter_by(id=lead.business_id, user_id=user_id).first()
        if not business:
            abort(404, description="Resource not found or unauthorized access.")
            
        kwargs["lead"] = lead
        kwargs["business"] = business
        return f(*args, **kwargs)
        
    return decorated_function
