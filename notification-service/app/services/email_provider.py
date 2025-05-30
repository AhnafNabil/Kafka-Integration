# notification-service/app/services/email_provider.py
import logging
import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, Any, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

class EmailProvider:
    """Provider for sending email notifications."""
    
    def __init__(self):
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.username = settings.SMTP_USER
        self.password = settings.SMTP_PASSWORD
        self.from_email = settings.EMAIL_FROM
        self.from_name = settings.EMAIL_FROM_NAME
        
        # Log the configuration at initialization
        logger.info(f"Email provider initialized with: Host={self.host}, Port={self.port}, User={self.username}")
    
    async def send_email(
        self, 
        to_email: str, 
        subject: str, 
        html_content: str, 
        text_content: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> bool:
        """
        Send an email notification.
        """
        # Log the email attempt with configuration details
        logger.info(f"Attempting to send email to {to_email} using {self.host}:{self.port}")
        
        # Skip if email configuration is missing
        if not self.username or not self.password or not self.from_email:
            logger.warning(f"Email configuration incomplete. Host: {self.host}, Port: {self.port}, User: {self.username}, From: {self.from_email}")
            return False
        
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email
            message["Subject"] = subject
            
            # Add CC if provided
            if cc:
                message["Cc"] = ", ".join(cc)
                
            # Add plain text version
            if text_content:
                message.attach(MIMEText(text_content, "plain", "utf-8"))
            else:
                # Generate plain text from HTML
                text_version = html_content.replace("<br>", "\n").replace("<br/>", "\n").replace("<p>", "\n").replace("</p>", "\n")
                message.attach(MIMEText(text_version, "plain", "utf-8"))
            
            # Add HTML version
            message.attach(MIMEText(html_content, "html", "utf-8"))
            
            # Build recipient list
            recipients = [to_email]
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)
            
            logger.info(f"Connecting to SMTP server {self.host}:{self.port}")
            
            # Send email with Mailtrap-specific configuration
            try:
                # For Mailtrap sandbox, we need different settings based on port
                if self.port == 2525:
                    # Port 2525 - Plain authentication, no TLS
                    smtp = aiosmtplib.SMTP(
                        hostname=self.host,
                        port=self.port,
                        use_tls=False,
                        start_tls=False
                    )
                    logger.info("Using plain authentication for port 2525")
                    
                    # Connect
                    await smtp.connect()
                    logger.info("Connected to SMTP server")
                    
                    # Login directly without TLS
                    await smtp.login(self.username, self.password)
                    logger.info("Logged in successfully")
                    
                elif self.port == 587:
                    # Port 587 - STARTTLS
                    smtp = aiosmtplib.SMTP(
                        hostname=self.host,
                        port=self.port,
                        use_tls=False,
                        start_tls=True
                    )
                    logger.info("Using STARTTLS for port 587")
                    
                    # Connect
                    await smtp.connect()
                    logger.info("Connected to SMTP server")
                    
                    # Start TLS
                    await smtp.starttls()
                    logger.info("TLS started")
                    
                    # Login
                    await smtp.login(self.username, self.password)
                    logger.info("Logged in successfully")
                    
                elif self.port == 465:
                    # Port 465 - SSL/TLS
                    smtp = aiosmtplib.SMTP(
                        hostname=self.host,
                        port=self.port,
                        use_tls=True,
                        start_tls=False
                    )
                    logger.info("Using SSL/TLS for port 465")
                    
                    # Connect
                    await smtp.connect()
                    logger.info("Connected to SMTP server")
                    
                    # Login
                    await smtp.login(self.username, self.password)
                    logger.info("Logged in successfully")
                    
                else:
                    # Default fallback
                    smtp = aiosmtplib.SMTP(
                        hostname=self.host,
                        port=self.port,
                    )
                    logger.info("Using default configuration")
                    
                    # Connect
                    await smtp.connect()
                    logger.info("Connected to SMTP server")
                    
                    # Login
                    await smtp.login(self.username, self.password)
                    logger.info("Logged in successfully")
                
                # Send the message
                await smtp.send_message(message)
                logger.info("Message sent successfully")
                
                # Quit
                await smtp.quit()
                logger.info("SMTP connection closed")
                
                logger.info(f"Email successfully sent to {to_email}")
                return True
                
            except Exception as e:
                logger.error(f"SMTP operation error: {str(e)}")
                raise
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False

# Create a singleton instance
email_provider = EmailProvider()