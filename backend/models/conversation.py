from models import db
from datetime import datetime
import json


class Conversation(db.Model):
    __tablename__ = "conversations"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(128), unique=True, nullable=False)  # sender IGSID
    business_id = db.Column(db.Integer, db.ForeignKey("businesses.id"), nullable=False)
    platform = db.Column(db.String(30), default="instagram")
    state = db.Column(db.String(50), default="idle")   # idle | capture_name | capture_phone | confirm_details | done
    temp_name = db.Column(db.String(120))               # Temp storage while capturing lead
    temp_phone = db.Column(db.String(120))              # Temp storage while capturing lead
    messages = db.Column(db.Text, default="[]")         # JSON list of {role, text, ts}
    last_active = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_messages(self):
        try:
            return json.loads(self.messages)
        except Exception:
            return []

    def add_message(self, role, text):
        msgs = self.get_messages()
        msgs.append({"role": role, "text": text, "ts": datetime.utcnow().isoformat()})
        self.messages = json.dumps(msgs)
        self.last_active = datetime.utcnow()

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "business_id": self.business_id,
            "platform": self.platform,
            "state": self.state,
            "messages": self.get_messages(),
            "last_active": self.last_active.isoformat() if self.last_active else None,
        }
