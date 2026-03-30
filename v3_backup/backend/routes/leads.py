"""Routes — Lead management API."""
from flask import Blueprint, jsonify, request
from models import db
from models.lead import Lead

leads_bp = Blueprint("leads", __name__)


@leads_bp.get("/api/leads/<int:business_id>")
def get_leads(business_id):
    leads = Lead.query.filter_by(business_id=business_id).order_by(Lead.captured_at.desc()).all()
    return jsonify([l.to_dict() for l in leads])


@leads_bp.patch("/api/leads/<int:lead_id>/convert")
def mark_converted(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    lead.is_converted = True
    db.session.commit()
    return jsonify(lead.to_dict())


@leads_bp.delete("/api/leads/<int:lead_id>")
def delete_lead(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    db.session.delete(lead)
    db.session.commit()
    return jsonify({"deleted": lead_id})


@leads_bp.get("/api/leads/<int:business_id>/export")
def export_leads(business_id):
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
