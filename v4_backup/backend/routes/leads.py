"""Routes — Lead management API."""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db
from models.lead import Lead
from models.business import Business

leads_bp = Blueprint("leads", __name__)


@leads_bp.get("/api/leads/<int:business_id>")
@jwt_required()
def get_leads(business_id):
    user_id = get_jwt_identity()
    Business.query.filter_by(id=business_id, user_id=user_id).first_or_404()
    leads = Lead.query.filter_by(business_id=business_id).order_by(Lead.captured_at.desc()).all()
    return jsonify([l.to_dict() for l in leads])


@leads_bp.patch("/api/leads/<int:lead_id>/convert")
@jwt_required()
def mark_converted(lead_id):
    user_id = get_jwt_identity()
    lead = Lead.query.get_or_404(lead_id)
    # Check if the business belongs to the user
    Business.query.filter_by(id=lead.business_id, user_id=user_id).first_or_404()
    lead.is_converted = True
    db.session.commit()
    return jsonify(lead.to_dict())


@leads_bp.delete("/api/leads/<int:lead_id>")
@jwt_required()
def delete_lead(lead_id):
    user_id = get_jwt_identity()
    lead = Lead.query.get_or_404(lead_id)
    # Check if the business belongs to the user
    Business.query.filter_by(id=lead.business_id, user_id=user_id).first_or_404()
    db.session.delete(lead)
    db.session.commit()
    return jsonify({"deleted": lead_id})


@leads_bp.get("/api/leads/<int:business_id>/export")
@jwt_required()
def export_leads(business_id):
    import io
    import csv
    from flask import Response

    user_id = get_jwt_identity()
    Business.query.filter_by(id=business_id, user_id=user_id).first_or_404()
    
    leads = Lead.query.filter_by(business_id=business_id).order_by(Lead.captured_at.desc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(["ID", "Name", "Phone", "Platform", "Captured At", "Converted"])
    
    for l in leads:
        writer.writerow([
            l.id,
            l.name,
            l.phone,
            l.platform,
            l.captured_at.strftime("%Y-%m-%d %H:%M:%S") if l.captured_at else "",
            "Yes" if l.is_converted else "No"
        ])
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename=leads_business_{business_id}.csv"}
    )
