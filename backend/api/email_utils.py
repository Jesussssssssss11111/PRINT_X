"""
Email utility for sending emails asynchronously in a background thread.
This prevents the HTTP request from waiting for email delivery.
"""

import threading
from django.core.mail import EmailMultiAlternatives
from django.conf import settings


def send_email_async(subject, text_body, html_body, recipient_email):
    """
    Send email in a background thread to avoid blocking the HTTP response.
    
    Args:
        subject: Email subject line
        text_body: Plain text version of email
        html_body: HTML version of email
        recipient_email: Recipient's email address
    
    Returns:
        None (email is sent in background)
    """
    def _send():
        try:
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient_email],
            )
            msg.attach_alternative(html_body, 'text/html')
            msg.send(fail_silently=False)
        except Exception as e:
            # Log error but don't crash the thread
            print(f"[EMAIL ERROR] Failed to send to {recipient_email}: {str(e)}")
    
    # Start email sending in background thread
    thread = threading.Thread(target=_send, daemon=True)
    thread.start()
