from models import db
from datetime import datetime


class Lead(db.Model):
    __tablename__ = "leads"

    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey("businesses.id"), nullable=False)
    platform = db.Column(db.String(30), default="instagram")
    sender_id = db.Column(db.String(64))        # Instagram IGSID
    name = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    note = db.Column(db.Text)                   # Any extra context from conversation
    is_converted = db.Column(db.Boolean, default=False)
    needs_attention = db.Column(db.Boolean, default=False)
    captured_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "business_id": self.business_id,
            "platform": self.platform,
            "sender_id": self.sender_id,
            "name": self.name,
            "phone": self.phone,
            "note": self.note,
            "is_converted": self.is_converted,
            "needs_attention": self.needs_attention,
            "captured_at": self.captured_at.isoformat() if self.captured_at else None,
        }
