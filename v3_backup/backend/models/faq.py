from models import db
from datetime import datetime
import json


class FAQ(db.Model):
    __tablename__ = "faqs"

    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey("businesses.id"), nullable=False)
    question = db.Column(db.String(255), nullable=False)     # Human-readable label
    keywords = db.Column(db.Text, nullable=False)            # JSON list of trigger keywords
    response = db.Column(db.Text, nullable=False)            # Reply text
    cta_label = db.Column(db.String(80))                     # e.g. "Book Now"
    cta_url = db.Column(db.String(512))                      # e.g. "https://calendly.com/..."
    priority = db.Column(db.Integer, default=0)              # Higher = matched first
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_keywords(self):
        try:
            return json.loads(self.keywords)
        except Exception:
            return []

    def to_dict(self):
        return {
            "id": self.id,
            "business_id": self.business_id,
            "question": self.question,
            "keywords": self.get_keywords(),
            "response": self.response,
            "cta_label": self.cta_label,
            "cta_url": self.cta_url,
            "priority": self.priority,
        }
