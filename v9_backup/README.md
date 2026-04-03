# ChatIQ — AI-Powered Instagram Chatbot for Small Businesses

Automate customer queries on Instagram 24/7. Built with Python Flask, SQLite, and OpenAI.

---

## 📁 Project Structure

```
Business Chatbot/
├── backend/
│   ├── app.py                  # Flask app factory
│   ├── config.py               # Configuration
│   ├── seed.py                 # DB seed script
│   ├── requirements.txt
│   ├── .env.example
│   ├── models/                 # SQLAlchemy models
│   │   ├── business.py
│   │   ├── faq.py
│   │   ├── lead.py
│   │   └── conversation.py
│   ├── routes/
│   │   ├── webhook.py          # Instagram webhook endpoints
│   │   ├── dashboard.py        # Business & FAQ CRUD API
│   │   └── leads.py            # Lead management API
│   ├── services/
│   │   ├── chatbot.py          # Core chatbot engine
│   │   ├── ai_service.py       # OpenAI GPT fallback
│   │   └── instagram.py        # Instagram Graph API
│   ├── data/businesses/        # Sample JSON configs
│   └── tests/
│       └── test_chatbot.py
└── frontend/
    ├── index.html              # Dashboard UI
    ├── css/styles.css
    └── js/app.js
```

---

## 🚀 Quick Start

### 1. Set up the backend

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and fill in your keys
```

### 3. Seed the database

```bash
python seed.py
```

### 4. Start the server

```bash
python app.py
# Server runs at http://localhost:5001
```

### 5. Open the dashboard

Open `http://localhost:5001` in your browser.
> ℹ️ The dashboard works in **demo mode** (with mock data) even without the backend running.

---

## 🧪 Test the Bot (Mock Mode)

With the server running, send a simulated Instagram DM:

```bash
curl -X POST http://localhost:5001/webhook/instagram \
  -H "Content-Type: application/json" \
  -d '{"entry":[{"id":"mockpage","messaging":[{"sender":{"id":"user123"},"message":{"text":"What are your prices?"}}]}]}'
```

The bot reply will appear in your terminal (MOCK_MODE=true).

---

## 🧪 Run Unit Tests

```bash
cd backend
python -m pytest tests/ -v
```

---

## ⚙️ Environment Variables

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | Your OpenAI API key (for AI fallback) |
| `INSTAGRAM_ACCESS_TOKEN` | Your Instagram Page access token |
| `INSTAGRAM_VERIFY_TOKEN` | Custom token for webhook verification |
| `INSTAGRAM_PAGE_ID` | Your Instagram Business Page ID |
| `MOCK_MODE` | `true` to skip real API calls (default: true) |

---

## 📸 Instagram Webhook Setup (Production)

1. Go to **Meta for Developers → Your App → Webhooks**
2. Subscribe to `messages` field for the Instagram product
3. Set Callback URL: `https://your-domain.com/webhook/instagram`
4. Set Verify Token: same as `INSTAGRAM_VERIFY_TOKEN` in your `.env`
5. Set `MOCK_MODE=false` in production

---

## 💰 Subscription Plans

| Plan | Price | Features |
|---|---|---|
| Trial | Free (3–5 days) | Instagram bot + 5 FAQs |
| Starter | ₹999/mo | Unlimited FAQs + lead capture |
| Growth | ₹1,999/mo | Analytics + AI replies |
| Pro | ₹2,999/mo | All features + priority support |
