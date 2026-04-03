# Razorpay Integration Guide for Lumis AI

Follow these steps to connect your Lumis AI platform to Razorpay for processing payments from Indian companies.

## 1. Get Your API Keys
1.  Log in to your [Razorpay Dashboard](https://dashboard.razorpay.com/).
2.  Navigate to **Settings** → **API Keys**.
3.  Click **Generate Key** (or use your existing ones).
4.  Copy the **Key ID** and **Key Secret**.

## 2. Update Environment Variables
Update the `.env` file on your AWS server (at `~/lumisai/backend/.env`) with your credentials:

```bash
# Razorpay Configuration
RAZORPAY_KEY_ID=rzp_live_xxxxxxxxxxxxxx
RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxxxxxxxxxx
RAZORPAY_WEBHOOK_SECRET=your_chosen_secret_string
```

## 3. Configure Webhooks
Webhooks are essential for automatically activating a business account after a successful payment.

1.  In your Razorpay Dashboard, go to **Settings** → **Webhooks**.
2.  Click **+ Add New Webhook**.
3.  **Webhook URL**: `https://lumisai.in/api/billing/webhook`
4.  **Secret**: Enter the same `RAZORPAY_WEBHOOK_SECRET` you defined in your `.env`.
5.  **Active Events**: Select `payment.captured`.
6.  Click **Create Webhook**.

## 4. Test the Integration
1.  **Test Mode**: Use your `rzp_test_...` keys first to verify the flow.
2.  **Live Mode**: Once verified, switch to `rzp_live_...` keys for real transactions.
3.  **Onboarding**: Try creating a new business and choosing a plan. The Razorpay modal should appear with the correct amount (Setup Fee + 1st Month).

## 5. Deployment
After updating your `.env` on the AWS server, restart the Docker container to apply the changes:

```bash
cd ~/lumisai
sudo docker compose up -d
```
