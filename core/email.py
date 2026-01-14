import os
from dotenv import load_dotenv
from core.logger import logger
import resend

load_dotenv()

RESEND_API_KEY = os.getenv("RESEND_API_KEY")

if not RESEND_API_KEY:
    logger.error("API key not found")

resend.api_key = RESEND_API_KEY

def send_reset_password_email(to_email : str , reset_link : str):
    
    try : 
        resend.emails.send(
            {
                "from": "Auth <onboarding@resend.dev>",
                "to":[to_email],
                "subject" : "Reset your password",
                 "html": f"""
                    <p>Hello,</p>
                    <p>You requested to reset your password.</p>
                    <p>
                        <a href="{reset_link}">
                            Click here to reset your password
                        </a>
                    </p>
                    <p>This link will expire in 10 minutes.</p>
                    <p>If you did not request this, please ignore this email.</p>
                """
            }
        )

        logger.info(f"Password reset email sent to {to_email}")

    except Exception :
        logger.error(
            f"Failed to send password reset email to {to_email}",
            exc_info=True
        )
