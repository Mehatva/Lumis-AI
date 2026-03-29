from models import db
from datetime import datetime


class Business(db.Model):
    __tablename__ = "businesses"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    niche = db.Column(db.String(60), nullable=False)          # gym, salon, cafe, etc.
    phone = db.Column(db.String(20))
    location = db.Column(db.String(255))
    location_url = db.Column(db.String(512))
    booking_url = db.Column(db.String(512))
    instagram_page_id = db.Column(db.String(64))
    access_token = db.Column(db.Text)                         # per-business Instagram token
    welcome_message = db.Column(db.Text, default="Hi! How can I help you today? 😊")
    tone = db.Column(db.String(30), default="friendly")       # friendly / professional / casual
    plan = db.Column(db.String(20), default="trial")          # trial / starter / growth / pro
    trial_expires_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    api_key = db.Column(db.String(64), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    faqs = db.relationship("FAQ", backref="business", lazy=True, cascade="all, delete-orphan")
    leads = db.relationship("Lead", backref="business", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "niche": self.niche,
            "phone": self.phone,
            "location": self.location,
            "location_url": self.location_url,
            "booking_url": self.booking_url,
            "instagram_page_id": self.instagram_page_id,
            "welcome_message": self.welcome_message,
            "tone": self.tone,
            "plan": self.plan,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
