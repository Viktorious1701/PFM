"""Invitation email body (US-01-01 AC-5)."""

from app.services.email.sender import EmailMessage

SUBJECT = "You have been invited to PFM (Family Budget Tracker)"

_TEXT = """\
Hi,

You have been invited to join the family budget tracker.

Open this link to set your name and password and activate your account:

{activation_url}

The link expires in {ttl_hours} hours. If it expires, ask for a new invitation.

If you were not expecting this, you can ignore this email — no account is
usable until the link is opened.
"""

_HTML = """\
<html>
  <body style="font-family: -apple-system, Segoe UI, Roboto, sans-serif; line-height: 1.5;">
    <h2 style="margin-bottom: 0.2em;">You've been invited to PFM</h2>
    <p>You have been invited to join the family budget tracker.</p>
    <p>
      <a href="{activation_url}"
         style="display:inline-block;padding:10px 18px;background:#2563eb;color:#fff;
                text-decoration:none;border-radius:6px;">Activate my account</a>
    </p>
    <p style="color:#555;font-size:0.9em;">
      This link expires in {ttl_hours} hours. If the button does not work, copy this
      URL into your browser:<br>
      <code style="word-break:break-all;">{activation_url}</code>
    </p>
  </body>
</html>
"""


def build_invitation_email(*, recipient: str, activation_url: str, ttl_hours: int) -> EmailMessage:
    return EmailMessage(
        to=recipient,
        subject=SUBJECT,
        text_body=_TEXT.format(activation_url=activation_url, ttl_hours=ttl_hours),
        html_body=_HTML.format(activation_url=activation_url, ttl_hours=ttl_hours),
    )
