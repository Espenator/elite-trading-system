"""
Email Alerts - Send email notifications
"""

import os
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict

from core.logger import get_logger

logger = get_logger(__name__)

# Load environment variables
load_dotenv()

class EmailAlerter:
    """
    Send trading alerts via email
    """
    
    def __init__(self):
        self.smtp_server = os.getenv('EMAIL_SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('EMAIL_SMTP_PORT', 587))
        self.sender_email = os.getenv('EMAIL_SENDER')
        self.sender_password = os.getenv('EMAIL_PASSWORD')
        self.recipient_email = os.getenv('EMAIL_RECIPIENT')
        
        self.enabled = bool(self.sender_email and self.sender_password and self.recipient_email)
        
        if self.enabled:
            logger.info("✅ Email alerts initialized")
        else:
            logger.warning("⚠️  Email not configured (check .env)")
    
    async def send_email(self, subject: str, body: str, html: bool = False):
        """
        Send email
        
        Args:
            subject: Email subject
            body: Email body (text or HTML)
            html: True if body is HTML
        """
        if not self.enabled:
            return
        
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = self.sender_email
            msg['To'] = self.recipient_email
            msg['Subject'] = subject
            
            if html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            logger.info(f"Email sent: {subject}")
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
    
    async def send_daily_summary(self, stats: Dict):
        """Send daily performance summary"""
        subject = f"📊 Daily Summary - {stats['daily_pnl']:+,.0f}"
        
        body = f"""
Elite Trading System - Daily Summary

Trades Today: {stats['total_trades']}
Wins: {stats['wins']} ({stats['win_rate']:.1f}%)
Losses: {stats['losses']}

Daily P&L: ${stats['daily_pnl']:,.2f}
Total Return: {stats['return_pct']:.1f}%

Active Positions: {stats['active_positions']}

---
Elite Trading System
"""
        await self.send_email(subject, body)

# Global instance
email_alerter = EmailAlerter()

# =============================================================================
# MANUAL TESTING
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        if not email_alerter.enabled:
            print("❌ Email not configured")
            return
        
        print("📧 Testing email alerts...")
        await email_alerter.send_email(
            subject="Test from Elite Trading System",
            body="This is a test email."
        )
        print("✅ Check your inbox!")
    
    asyncio.run(test())
