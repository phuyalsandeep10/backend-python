
from src.config.mail import mail_sender
import dramatiq


@dramatiq.actor
def send_roleinvitation_email(email: str):
    print(f"Sending invitation email to {email}")
    mail_sender.send(
        subject="Invitation",
        recipients=[email],
        body_html="Invitation email. Your invitation is pending.",
        body_text="This is a test email.",
    )

@dramatiq.actor
def send_customer_welcome_mail(email: str,organization:str):
    print(f"Sending welcome mail to {email}")
    mail_sender.send(
        subject=f"Customer Join",
        recipients=[email],
        body_html=f"Welcome to {organization}.",
        body_text="This is a test email.",
    )


@dramatiq.actor
def send_invitation_email(email: str, html_context: str):
    print(f"Sending role invitation email to {email}")
    mail_sender.send(
        subject="You're Invited to our Organization Role",
        recipients=[email],
        body_html=html_context,
        body_text="You have been invited to join our organization role",
    )
