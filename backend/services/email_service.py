import os
from flask import current_app

class EmailService:
    """
    Modular Email Service for SaaS alerts (80% usage, Welcome, etc.)
    Currently logs to console for demo, ready for SendGrid/SES integration.
    """

    @staticmethod
    def send_usage_alert(business, percentage):
        """
        Sends an alert to the business owner when they hit a usage threshold.
        """
        subject = f"⚠️ Action Required: Lumis AI Usage at {percentage}%"
        
        # In a real SaaS, we'd fetch the owner's email from the User model
        # For now, we'll log it clearly as requested
        msg = (
            f"Dear {business.name} Team,\n\n"
            f"You have used {business.credits_used} out of {business.credits_limit} AI messages "
            f"({percentage}%) for the current billing cycle.\n\n"
            "To ensure your Instagram bot continues to reply without interruption, "
            "we recommend upgrading to a higher tier now.\n\n"
            "Upgrade here: https://lumisai.in/dashboard/billing\n\n"
            "Stay automated,\nThe Lumis AI Team"
        )
        
        # LOGGING (Placeholder for actual SMTP/API call)
        current_app.logger.warning(f"[EMAIL ALERT] {subject}")
        print(f"--- EMAIL SENT TO OWNER ---\nSubject: {subject}\n\n{msg}\n---------------------------")
        
        return True

    @staticmethod
    def send_limit_reached(business):
        """
        Sends a critical alert when the bot is stopped due to limit.
        """
        subject = "🚫 CRITICAL: Lumis AI Service Paused (Limit Reached)"
        msg = (
            f"Your bot for {business.name} has reached its monthly limit of {business.credits_limit} messages.\n"
            "AI automation is currently paused and will resume once you upgrade or the cycle resets.\n\n"
            "Upgrade Now: https://lumisai.in/dashboard/billing"
        )
        current_app.logger.error(f"[EMAIL ALERT] {subject}")
        print(f"--- EMAIL SENT TO OWNER ---\nSubject: {subject}\n\n{msg}\n---------------------------")
        return True
