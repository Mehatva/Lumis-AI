"""Routes — Lead management API."""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db
from models.lead import Lead
from models.business import Business
from utils.auth_utils import business_owned, lead_owned

leads_bp = Blueprint("leads", __name__)


@leads_bp.get("/api/leads/<int:business_id>")
@jwt_required()
@business_owned
def get_leads(business_id, business=None):
    # HARD GATE: If no paid plan yet, restrict leads access
    if business.plan == "trial":
        return jsonify({
            "error": "Payment Required",
            "message": "Please complete your onboarding and select a plan to unlock your Lead Inbox."
        }), 402

    leads = Lead.query.filter_by(business_id=business_id).order_by(Lead.captured_at.desc()).all()
    return jsonify([l.to_dict() for l in leads])


@leads_bp.patch("/api/leads/<int:lead_id>/convert")
@jwt_required()
@lead_owned
def mark_converted(lead_id, lead=None, business=None):
    lead.is_converted = True
    db.session.commit()
    return jsonify(lead.to_dict())


@leads_bp.delete("/api/leads/<int:lead_id>")
@jwt_required()
@lead_owned
def delete_lead(lead_id, lead=None, business=None):
    db.session.delete(lead)
    db.session.commit()
    return jsonify({"deleted": lead_id})


@leads_bp.get("/api/leads/<int:business_id>/export")
@jwt_required()
@business_owned
def export_leads(business_id, business=None):
    import io
    import csv
    from flask import Response

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
