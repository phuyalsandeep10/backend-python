import logging

from cryptography.fernet import Fernet
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Email, Mail

from src.config.settings import settings

logger = logging.getLogger(__name__)

key = settings.SECRET_FERNET_KEY.encode()
fernet = Fernet(key)


# 2. Encode IDs
def encode_ticket(org_id: int, ticket_id: int) -> str:
    data = f"{org_id}:{ticket_id}".encode()
    token = fernet.encrypt(data)
    return f"tickets_{token.decode()}"


def decode_ticket(encoded: str) -> tuple[int, int]:
    if not encoded.startswith("tickets_"):
        raise ValueError("Invalid token prefix")
    token = encoded[len("tickets_") :]
    data = fernet.decrypt(token.encode()).decode()
    org_id, ticket_id = map(int, data.split(":"))
    return org_id, ticket_id


def get_recent_reply(full_text: str) -> str:
    """
    Extract only the most recent reply from an email body.
    """
    lines = full_text.splitlines()
    recent_lines = []

    for line in lines:
        # Stop if this line looks like a previous message
        if (
            line.startswith(">")
            or "wrote:" in line
            or (line.startswith("On ") and "<" in line)
        ):
            break
        recent_lines.append(line)

    return "\n".join(recent_lines).strip()


def send_sendgrid_email(
    from_email: tuple[str, str],
    to_email: str,
    subject: str,
    html_content: str,
    ticket_id: int,
    org_id: int,
):
    try:
        message = Mail(
            from_email=Email(from_email[0], from_email[1]),
            to_emails=to_email,
            subject=subject,
            html_content=html_content,
        )
        reply = encode_ticket(org_id=org_id, ticket_id=ticket_id)

        message.reply_to = Email(f"{reply}@reply.{settings.EMAIL_DOMAIN}", "Reply To")

        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(message)
    except Exception as e:
        logger.exception(e)
